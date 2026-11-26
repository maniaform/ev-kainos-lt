import os
import re
import requests
from bs4 import BeautifulSoup

VIA_API_URL = "https://" + "ev.vialietuva" + ".lt/api/locations/all"
TAVILY_URL = "https://" + "api.tavily" + ".com/search"

OPERATORIU_PUSLAPIAI = {
    "Eleport": "https://" + "eleport" + ".com/charging/"
}

def normalizuoti_operatoriu(raw_name, stoteles_pav=""):
    t = f"{raw_name} {stoteles_pav}".lower()
    if "ignitis" in t: return "Ignitis ON"
    if "eleport" in t: return "Eleport"
    if "elinta" in t: return "Elinta Charge"
    if "in balance" in t or "inbalance" in t: return "Inbalance grid"
    if "enefit" in t: return "Enefit Volt"
    if "lidl" in t: return "Lidl"
    if "tesla" in t: return "Tesla Supercharger"
    if "ionity" in t: return "Ionity"
    if "circle k" in t: return "Circle K"
    if "neste" in t: return "Neste"
    if "virta" in t: return "Virta"
    if "stoti" in t: return "Stoti"
    if "eni" in t or "enel" in t: return "Enel X"
    # Sutrumpiname UAB, AB ir pan.
    clean = re.sub(r',?\s*\b(UAB|AB|MB|VšĮ|IĮ)\b\.?', '', raw_name, flags=re.IGNORECASE).strip()
    return clean if clean else "Kiti operatoriai"

def normalizuoti_jungti(sdr_code):
    code = (sdr_code or "").upper()
    if "COMBO" in code or "CCS" in code:
        return "CCS2"
    if "CHADEMO" in code:
        return "CHAdeMO"
    if "T2" in code or "TYPE_2" in code or "MENNEKES" in code:
        return "Type 2"
    return code if code else "Type 2"

def istraukti_kaina_is_teksto(price_str):
    if not price_str:
        return None, False
    p_low = str(price_str).lower().strip()
    if "free" in p_low or "nemokam" in p_low:
        return 0.0, True
    m = re.search(r'(\d+[.,]\d+)', p_low)
    if m:
        try:
            val = float(m.group(1).replace(',', '.'))
            # Skaičius 0.00 be žodžio "nemokama" dažniausiai reiškia tuščią registro lauką, o ne nemokamą įkrovimą
            if 0.05 <= val <= 3.00:
                return round(val, 2), False
        except ValueError:
            pass
    return None, False
    
def surinkti_ev_stoteles():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }

    visos_eilutes = []
    offset = 0
    limit = 500

    while True:
        try:
            res = requests.get(VIA_API_URL, params={"limit": limit, "offset": offset}, headers=headers, timeout=25)
            res.raise_for_status()
            data = res.json()
            rows = data.get("rows") or []
            if not rows:
                break
            visos_eilutes.extend(rows)
            print(f"Paimta {len(visos_eilutes)} stotelių iš VIA Lietuva API...")
            if len(rows) < limit:
                break
            offset += limit
        except Exception as e:
            print(f"Klaida skaitant VIA Lietuva API (offset={offset}):", e)
            break

    stoteles = []
    for item in visos_eilutes:
        miestas = (item.get("c") or "Lietuva").strip()
        adresas = (item.get("adr") or item.get("n") or "").strip()
        if not adresas:
            continue

        op_obj = item.get("o") or item.get("own") or {}
        raw_op_name = op_obj.get("name") or ""
        operatorius = normalizuoti_operatoriu(raw_op_name, item.get("n") or "")

        evses = item.get("e") or []
        max_kw = 0.0
        jungciu_tipai = set()
        dc_kainos = []
        ac_kainos = []
        yra_nemokama = False
        laisvu_jungciu = 0

        for evse in evses:
            if (evse.get("s") or "").upper() == "AVAILABLE":
                laisvu_jungciu += 1
            for conn in (evse.get("c") or []):
                kw = float(conn.get("kw") or 0)
                if kw > max_kw:
                    max_kw = kw
                j_tipas = normalizuoti_jungti(conn.get("sdr"))
                jungciu_tipai.add(j_tipas)

                kaina_val, is_free = istraukti_kaina_is_teksto(conn.get("price"))
                if is_free:
                    yra_nemokama = True
                if kaina_val is not None:
                    is_dc_conn = kw >= 40 or j_tipas in ["CCS2", "CHAdeMO"]
                    if is_dc_conn:
                        dc_kainos.append(kaina_val)
                    else:
                        ac_kainos.append(kaina_val)

        if not jungciu_tipai:
            jungciu_tipai.add("Type 2" if max_kw <= 22 else "CCS2")

        is_dc_station = max_kw >= 40 or ("CCS2" in jungciu_tipai or "CHAdeMO" in jungciu_tipai)
        min_dc = min(dc_kainos) if dc_kainos else None
        min_ac = min(ac_kainos) if ac_kainos else None
        pagrindine_kaina = min_dc if is_dc_station else min_ac
        if pagrindine_kaina is None:
            pagrindine_kaina = min_dc if min_dc is not None else min_ac

        stoteles.append({
            "operator": operatorius,
            "city": miestas,
            "address": adresas,
            "connectors": sorted(list(jungciu_tipai)),
            "power_kw": round(max_kw, 1) if max_kw else 22.0,
            "is_dc": is_dc_station,
            "is_free": yra_nemokama or (pagrindine_kaina == 0.0),
            "dc_price": min_dc,
            "ac_price": min_ac,
            "price": pagrindine_kaina,
            "available_count": laisvu_jungciu,
            "website": op_obj.get("website") or ""
        })

    print(f"Iš viso apdorota {len(stoteles)} oficialių EV stotelių.")
    return stoteles

def nuskaityti_oficialius_puslapius():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    surinktas_tekstas = []
    for op_name, url in OPERATORIU_PUSLAPIAI.items():
        try:
            r = requests.get(url, headers=headers, timeout=12)
            if r.ok:
                soup = BeautifulSoup(r.text, "html.parser")
                if op_name == "Eleport":
                    lt_blokas = soup.find(attrs={"data-id": "bb01b44"})
                    if lt_blokas:
                        lt_tekstas = " ".join(lt_blokas.get_text(separator=" ").split())
                        surinktas_tekstas.append(f"=== OFICIALUS PUSLAPIS (LIETUVA): {op_name} ({url}) ===\n{lt_tekstas}")
        except Exception:
            pass
    return "\n".join(surinktas_tekstas)

def gauti_ev_tarifu_konteksta():
    return nuskaityti_oficialius_puslapius()
