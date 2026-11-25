import os
import requests

OCM_URL = "https://" + "api.openchargemap" + ".io/v3/poi"
TAVILY_URL = "https://" + "api.tavily" + ".com/search"

def isvalyti_miesta(adr_info):
    town = (adr_info.get("Town") or "").strip()
    if town:
        return town.split(",")[0].strip()
    state = (adr_info.get("StateOrProvince") or "").strip()
    if state:
        return state.replace("apskritis", "").strip()
    return "Lietuva"

def nustatyti_operatoriu(item):
    op_info = item.get("OperatorInfo") or {}
    op_title = (op_info.get("Title") or "").lower()
    adr = item.get("AddressInfo") or {}
    visas_tekstas = f"{op_title} {adr.get('Title', '')} {adr.get('AddressLine1', '')} {item.get('GeneralComments', '')}".lower()

    if "ignitis" in visas_tekstas: return "Ignitis ON"
    if "eleport" in visas_tekstas: return "Eleport"
    if "elinta" in visas_tekstas: return "Elinta Charge"
    if "inbalance" in visas_tekstas: return "Inbalance grid"
    if "enefit" in visas_tekstas: return "Enefit Volt"
    if "lidl" in visas_tekstas: return "Lidl"
    if "tesla" in visas_tekstas: return "Tesla Supercharger"
    if "ionity" in visas_tekstas: return "Ionity"
    if "circle k" in visas_tekstas: return "Circle K"
    if "neste" in visas_tekstas: return "Neste"
    if "virta" in visas_tekstas: return "Virta"
    if op_info.get("Title") and "unknown" not in op_title:
        return op_info.get("Title").strip()
    return "Savivaldybių / Kitos stotelės"

def surinkti_ev_stoteles():
    ocm_key = (os.environ.get("OCM_API_KEY") or "").strip()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) EVKainosLT/1.0",
        "Accept": "application/json"
    }
    params = {
        "output": "json",
        "countrycode": "LT",
        "maxresults": 1500,
        "compact": "false",
        "verbose": "false"
    }
    if ocm_key:
        headers["X-API-Key"] = ocm_key
        params["key"] = ocm_key

    try:
        res = requests.get(OCM_URL, params=params, headers=headers, timeout=25)
        res.raise_for_status()
        raw_stations = res.json()
        print(f"Gauta {len(raw_stations)} EV stotelių iš Open Charge Map.")
    except Exception as e:
        print("Klaida skaitant Open Charge Map API:", e)
        raw_stations = []

    jungtys_map = {
        33: "CCS2",
        25: "Type 2",
        2: "CHAdeMO",
        1036: "Type 2"
    }

    stoteles = []
    for item in raw_stations:
        adr = item.get("AddressInfo") or {}
        adresas = (adr.get("AddressLine1") or adr.get("Title") or "").strip()
        if not adresas:
            continue

        miestas = isvalyti_miesta(adr)
        operatorius = nustatyti_operatoriu(item)

        connections = item.get("Connections") or []
        max_kw = 0
        jungciu_tipai = set()
        for conn in connections:
            kw = conn.get("PowerKW") or 0
            if kw > max_kw:
                max_kw = kw
            c_type = jungtys_map.get(conn.get("ConnectionTypeID"))
            if c_type:
                jungciu_tipai.add(c_type)

        if not jungciu_tipai:
            jungciu_tipai.add("Type 2" if max_kw <= 22 else "CCS2")

        usage_cost = str(item.get("UsageCost") or "").lower()
        nemokama = "free" in usage_cost or "0.00" in usage_cost

        stoteles.append({
            "operator": operatorius,
            "city": miestas,
            "address": adresas,
            "connectors": sorted(list(jungciu_tipai)),
            "power_kw": round(float(max_kw), 1) if max_kw else 22.0,
            "is_dc": max_kw >= 40 or ("CCS2" in jungciu_tipai or "CHAdeMO" in jungciu_tipai),
            "is_free": nemokama,
            "raw_cost": item.get("UsageCost") or ""
        })

    return stoteles

def gauti_ev_tarifu_konteksta():
    api_key = (os.environ.get("TAVILY_API_KEY") or "").strip()
    if not api_key:
        return ""
    queries = [
        "Ignitis ON įkrovimo kaina kWh DC AC tarifai",
        "Eleport įkrovimo kainos kWh Lietuva DC AC",
        "Elinta Charge įkrovimo kaina kWh tarifai",
        "Inbalance grid įkrovimo kaina kWh tarifai",
        "Enefit Volt įkrovimo kaina kWh Lietuva",
        "Lidl įkrovimo stotelės kaina kWh Lietuvoje",
        "Ionity Tesla Supercharger įkrovimo kaina kWh Lietuva",
        "Circle K Neste įkrovimo kaina kWh Lietuvoje"
    ]
    rezultatai = []
    for q in queries:
        try:
            r = requests.post(
                TAVILY_URL,
                json={"api_key": api_key, "query": q, "search_depth": "basic", "max_results": 2},
                timeout=15
            )
            if r.ok:
                for item in r.json().get("results", []):
                    rezultatai.append(f"[{item.get('title')} ({item.get('url')})]: {item.get('content')}")
        except Exception:
            pass
    return "\n".join(rezultatai)
