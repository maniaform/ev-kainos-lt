import re
import json
from datetime import datetime
from scraper import surinkti_ev_stoteles, gauti_ev_tarifu_konteksta
from analyzer import nustatyti_operatoriu_tarifus
from seo import generuoti_ev_seo

OPERATOR_LOGOS = {
    "Ignitis ON": "https://google.com",
    "Eleport": "https://google.com",
    "Elinta Charge": "https://google.com",
    "Inbalance grid": "https://google.com",
    "Enefit Volt": "https://google.com",
    "Lidl": "https://google.com",
    "Tesla Supercharger": "https://google.com",
    "Ionity": "https://google.com",
    "Circle K": "https://google.com",
    "Neste": "https://google.com",
    "Virta": "https://google.com"
}

OPERATOR_URLS = {
    "Ignitis ON": "https://ignitison.lt",
    "Eleport": "https://eleport.com",
    "Elinta Charge": "https://elintacharge.com",
    "Inbalance grid": "https://inbalancegrid.com",
    "Enefit Volt": "https://enefitvolt.lt",
    "Lidl": "https://lidl.lt",
    "Tesla Supercharger": "https://tesla.com",
    "Ionity": "https://ionity.eu",
    "Circle K": "https://circlek.lt",
    "Neste": "https://neste.lt",
    "Virta": "https://virta.global"
}

def sukurti_id(pavadinimas):
    p = pavadinimas.lower().strip()
    lt = {'ą': 'a', 'č': 'c', 'ę': 'e', 'ė': 'e', 'į': 'i', 'š': 's', 'ų': 'u', 'ū': 'u', 'ž': 'z'}
    for k, v in lt.items():
        p = p.replace(k, v)
    return re.sub(r'[^a-z0-9]+', '-', p).strip('-')

def paleisti_ev_atnaujinima():
    dabar = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"[{dabar}] Pradedamas EV įkrovimo stotelių ir kainų surinkimas...")

    seni_duomenys = {}
    try:
        with open("ev_prices.json", "r", encoding="utf-8") as f:
            seni_duomenys = json.load(f)
    except FileNotFoundError:
        pass

    stoteles = surinkti_ev_stoteles()
    paieskos_tekstas = gauti_ev_tarifu_konteksta()

    try:
        di_rezultatas = nustatyti_operatoriu_tarifus(paieskos_tekstas, dabar)
        tarifai = di_rezultatas.get("tariffs") or {}
    except Exception as e:
        print("Klaida nustatant tarifus per DI:", e)
        di_rezultatas = {}
        tarifai = {}

    seni_tinklai_map = {n["id"]: n for n in seni_duomenys.get("networks", [])}
    tinklai_dict = {}

    for st in stoteles:
        op_name = st["operator"]
        op_id = sukurti_id(op_name)
        tarifai_lower = {k.lower(): v for k, v in tarifai.items()}
        op_tarifas = tarifai.get(op_name) or tarifai_lower.get(op_name.lower()) or {}

        ocm_kaina = None
        if st["is_free"]:
            ocm_kaina = 0.0
        elif st.get("raw_cost"):
            m = re.search(r'(\d+[.,]\d+)', str(st["raw_cost"]))
            if m:
                try:
                    val = float(m.group(1).replace(',', '.'))
                    if 0.05 <= val <= 2.50:
                        ocm_kaina = round(val, 2)
                except ValueError:
                    pass

        dc_kaina = ocm_kaina if ocm_kaina is not None else op_tarifas.get("dc")
        ac_kaina = ocm_kaina if ocm_kaina is not None else op_tarifas.get("ac")

        if op_id not in tinklai_dict:
            senas_net = seni_tinklai_map.get(op_id, {})
            tinklai_dict[op_id] = {
                "id": op_id,
                "name": op_name,
                "logo_url": OPERATOR_LOGOS.get(op_name, ""),
                "best_dc": None,
                "best_ac": None,
                "diff_dc": 0,
                "diff_ac": 0,
                "max_power_kw": 0,
                "price_time": dabar,
                "source_name": "Open Charge Map / Operatoriai",
                "source_url": op_tarifas.get("source_url") or "https://openchargemap.org",
                "stations": [],
                "_old_dc": senas_net.get("best_dc"),
                "_old_ac": senas_net.get("best_ac")
            }

        st_kaina = dc_kaina if st["is_dc"] else ac_kaina
        tinklai_dict[op_id]["stations"].append({
            "city": st["city"],
            "address": st["address"],
            "connectors": st["connectors"],
            "power_kw": st["power_kw"],
            "is_dc": st["is_dc"],
            "is_free": st["is_free"],
            "dc_price": dc_kaina if st["is_dc"] else None,
            "ac_price": ac_kaina if not st["is_dc"] else None,
            "price": st_kaina,
            "time": dabar
        })

        if st["power_kw"] > tinklai_dict[op_id]["max_power_kw"]:
            tinklai_dict[op_id]["max_power_kw"] = st["power_kw"]

    atnaujinti_tinklai = []
    for op_id, net in tinklai_dict.items():
        dc_kainos = [s["dc_price"] for s in net["stations"] if isinstance(s.get("dc_price"), (int, float))]
        ac_kainos = [s["ac_price"] for s in net["stations"] if isinstance(s.get("ac_price"), (int, float))]

        if dc_kainos:
            nauja_dc = min(dc_kainos)
            net["best_dc"] = nauja_dc
            if isinstance(net["_old_dc"], (int, float)):
                net["diff_dc"] = round(nauja_dc - net["_old_dc"], 3)

        if ac_kainos:
            nauja_ac = min(ac_kainos)
            net["best_ac"] = nauja_ac
            if isinstance(net["_old_ac"], (int, float)):
                net["diff_ac"] = round(nauja_ac - net["_old_ac"], 3)

        del net["_old_dc"]
        del net["_old_ac"]
        atnaujinti_tinklai.append(net)

    galutinis = {
        "last_updated": dabar,
        "summary_dc": di_rezultatas.get("summary_dc", seni_duomenys.get("summary_dc", "Greitojo DC įkrovimo stotelių duomenys atnaujinti.")),
        "summary_ac": di_rezultatas.get("summary_ac", seni_duomenys.get("summary_ac", "Lėtesnio AC įkrovimo stotelių duomenys atnaujinti.")),
        "networks": atnaujinti_tinklai
    }

    with open("ev_prices.json", "w", encoding="utf-8") as f:
        json.dump(galutinis, f, ensure_ascii=False, indent=2)

    generuoti_ev_seo(galutinis)
    print(f"Sėkmingai atnaujinta {len(atnaujinti_tinklai)} operatorių, {len(stoteles)} EV stotelių ir visi SEO puslapiai!")

if __name__ == "__main__":
    paleisti_ev_atnaujinima()
