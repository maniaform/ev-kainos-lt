import os
import json
import requests

GROQ_URL = "https://groq.com"

def siusti_groq(promptas, max_tokens=1500):
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("Nerastas GROQ_API_KEY raktas!")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
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
{paieskos_tekstas[:5500]}

Nustatyk pagrindinių Lietuvos EV tinklų vidutines kainas (€/kWh) greitajam (DC) ir lėtajam (AC) įkrovimui.
Jei tikslaus skaičiaus tekste nėra, naudok realius žinomus Lietuvos rinkos tarifus (pvz., Ignitis ON DC ~0.49, AC ~0.37; Eleport DC ~0.48, AC ~0.35; Elinta Charge DC ~0.45, AC ~0.33; Inbalance grid DC ~0.46, AC ~0.34; Lidl DC ~0.39, AC ~0.29; Ionity DC ~0.69; Tesla Supercharger DC ~0.44; Virta DC ~0.47, AC ~0.35).

GRIEŽTA TAISYKLĖ: Niekada nerašyk programavimo terminų („null“, „None“, „duomenyse nenurodyta“). Rašyk tik aiškią, vairuotojams suprantamą informaciją lietuvių kalba.

Grąžink JSON objektą su šiais raktais:
- "tariffs": objektas, kur raktas yra tikslus operatoriaus pavadinimas ("Ignitis ON", "Eleport", "Elinta Charge", "Inbalance grid", "Lidl", "Ionity", "Tesla Supercharger", "Virta"), o reikšmė {{"dc": 0.49, "ac": 0.37, "source_url": "https://..."}}
- "summary_dc": 2 sakinių apžvalga vairuotojams apie mažiausias greitojo DC įkrovimo kainas Lietuvoje.
- "summary_ac": 2 sakinių apžvalga vairuotojams apie mažiausias lėtesnio AC įkrovimo kainas Lietuvoje."""
    return siusti_groq(promptas)
