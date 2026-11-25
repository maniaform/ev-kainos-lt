import os
import json
import requests

GROQ_URL = "https://" + "api.groq" + ".com/openai/v1/chat/completions"

NUMATYTIEJI_TARIFAI = {
    "Ignitis ON": {"dc": 0.49, "ac": 0.37, "source_url": "https://ignitison.lt"},
    "Eleport": {"dc": 0.48, "ac": 0.35, "source_url": "https://eleport.com"},
    "Elinta Charge": {"dc": 0.45, "ac": 0.33, "source_url": "https://elintacharge.com"},
    "Inbalance grid": {"dc": 0.46, "ac": 0.34, "source_url": "https://inbalancegrid.com"},
    "Enefit Volt": {"dc": 0.47, "ac": 0.35, "source_url": "https://enefitvolt.lt"},
    "Lidl": {"dc": 0.39, "ac": 0.29, "source_url": "https://lidl.lt"},
    "Tesla Supercharger": {"dc": 0.44, "ac": 0.35, "source_url": "https://tesla.com"},
    "Ionity": {"dc": 0.69, "ac": 0.49, "source_url": "https://ionity.eu"},
    "Circle K": {"dc": 0.52, "ac": 0.39, "source_url": "https://circlek.lt"},
    "Neste": {"dc": 0.49, "ac": 0.37, "source_url": "https://neste.lt"},
    "Virta": {"dc": 0.47, "ac": 0.35, "source_url": "https://virta.global"},
    "Savivaldybių / Kitos stotelės": {"dc": 0.42, "ac": 0.30, "source_url": "https://openchargemap.org"}
}

def siusti_groq(promptas, max_tokens=1500):
    api_key = (os.environ.get("GROQ_API_KEY") or "").strip()
    if not api_key:
        raise ValueError("Nerastas GROQ_API_KEY raktas!")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system",
                "content": "Esi tikslus Lietuvos elektromobilių įkrovimo rinkos analitikas. Grąžink TIK gryną JSON objektą be jokio papildomo teksto."
            },
            {
                "role": "user",
                "content": promptas
            }
        ],
        "temperature": 0.1,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"}
    }
    res = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
    res.raise_for_status()
    return json.loads(res.json()["choices"]["message"]["content"])

def nustatyti_operatoriu_tarifus(paieskos_tekstas, dabar_str):
    promptas = f"""Remdamasis šiais paieškos duomenimis apie EV įkrovimo kainas Lietuvoje ({dabar_str}):
{paieskos_tekstas[:4500]}

Patikslink Lietuvos EV tinklų kainas (€/kWh) greitajam (DC) ir lėtajam (AC) įkrovimui. Jei tekste kainos nėra, naudok šiuos bazinius tarifus: Ignitis ON (DC 0.49, AC 0.37), Eleport (DC 0.48, AC 0.35), Elinta Charge (DC 0.45, AC 0.33), Inbalance grid (DC 0.46, AC 0.34), Enefit Volt (DC 0.47, AC 0.35), Lidl (DC 0.39, AC 0.29), Ionity (DC 0.69), Tesla Supercharger (DC 0.44), Circle K (DC 0.52).

Grąžink JSON objektą su raktais:
- "tariffs": objektas su operatorių pavadinimais ir {{"dc": 0.49, "ac": 0.37}}
- "summary_dc": 2 sakinių apžvalga vairuotojams apie mažiausias greitojo DC įkrovimo kainas Lietuvoje.
- "summary_ac": 2 sakinių apžvalga vairuotojams apie mažiausias lėtesnio AC įkrovimo kainas Lietuvoje."""
    try:
        di_ats = siusti_groq(promptas)
        sujungti = dict(NUMATYTIEJI_TARIFAI)
        for op, val in (di_ats.get("tariffs") or {}).items():
            if op in sujungti and isinstance(val, dict):
                if isinstance(val.get("dc"), (int, float)):
                    sujungti[op]["dc"] = round(float(val["dc"]), 2)
                if isinstance(val.get("ac"), (int, float)):
                    sujungti[op]["ac"] = round(float(val["ac"]), 2)
        return {
            "tariffs": sujungti,
            "summary_dc": di_ats.get("summary_dc", "Greitojo DC įkrovimo kainos Lietuvoje šiandien prasideda nuo 0.39 €/kWh."),
            "summary_ac": di_ats.get("summary_ac", "Lėtesnio AC įkrovimo kainos Lietuvoje šiandien prasideda nuo 0.29 €/kWh.")
        }
    except Exception as e:
        print("Naudojami baziniai tarifai (DI atsarginis režimas):", e)
        return {
            "tariffs": NUMATYTIEJI_TARIFAI,
            "summary_dc": "Greitojo DC įkrovimo kainos Lietuvoje šiandien prasideda nuo 0.39 €/kWh (Lidl) ir 0.44 €/kWh (Tesla Supercharger).",
            "summary_ac": "Lėtesnio AC įkrovimo kainos Lietuvoje šiandien prasideda nuo 0.29 €/kWh (Lidl) ir 0.33 €/kWh (Elinta Charge)."
        }
