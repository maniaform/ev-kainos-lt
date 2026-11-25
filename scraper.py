import os
import requests

OCM_URL = "https://openchargemap.io"

def isvalyti_miesta(adr_info):
    town = (adr_info.get("Town") or "").strip()
    if town:
        return town.split(",").strip()
    state = (adr_info.get("StateOrProvince") or "").strip()
    if state:
        return state.replace("apskritis", "").strip()
    return "Lietuva"

def surinkti_ev_stoteles():
    ocm_key = os.environ.get("OCM_API_KEY", "")
    headers = {"User-Agent": "EVKainosLT/1.0"}
    if ocm_key:
        headers["X-API-Key"] = ocm_key

    params = {
        "countrycode": "LT",
        "maxresults": 1500,
        "compact": "true",
        "verbose": "false"
    }

    try:
        res = requests.get(OCM_URL, params=params, headers=headers, timeout=25)
        res.raise_for_status()
        raw_stations = res.json()
        print(f"Gauta {len(raw_stations)} EV stotelių iš Open Charge Map.")
    except Exception as e:
        print("Klaida skaitant Open Charge Map API:", e)
        raw_stations = []

    operatoriai_map = {
        1: "Ignitis ON",
        3392: "Eleport",
        3453: "Elinta Charge",
        3534: "Inbalance grid",
        45: "Lidl",
        23: "Tesla Supercharger",
        3299: "Ionity",
        3615: "Virta"
    }

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
        op_id = item.get("OperatorID")
        operatorius = operatoriai_map.get(op_id, "Kiti operatoriai")

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
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return ""
    queries = [
        "Ignitis ON įkrovimo kainos kWh DC AC Lietuvoje",
        "Eleport Elinta Charge Inbalance grid įkrovimo kainos kWh",
        "Ionity Lidl Tesla įkrovimo kaina kWh Lietuvoje"
    ]
    rezultatai = []
    for q in queries:
        try:
            r = requests.post(
                "https://tavily.com",
                json={"api_key": api_key, "query": q, "search_depth": "basic", "max_results": 3},
                timeout=15
            )
            if r.ok:
                for item in r.json().get("results", []):
                    rezultatai.append(f"[{item.get('title')}]: {item.get('content')}")
        except Exception:
            pass
    return "\n".join(rezultatai)
