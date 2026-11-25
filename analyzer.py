import os
import json
import requests

GROQ_URL = "https://" + "api.groq" + ".com/openai/v1/chat/completions"

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
                "content": "Esi griežtas faktų tikrintojas. Grąžink TIK gryną JSON objektą. Niekada neišsigalvok ir nespėliok kainų, jei jų nėra tekste."
            },
            {
                "role": "user",
                "content": promptas
            }
        ],
        "temperature": 0.0,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"}
    }
    res = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
    res.raise_for_status()
    return json.loads(res.json()["choices"]["message"]["content"])

def nustatyti_operatoriu_tarifus(paieskos_tekstas, dabar_str):
    promptas = f"""Išanalizuok šiuos paieškos duomenis apie elektromobilių įkrovimo kainas Lietuvoje ({dabar_str}):
{paieskos_tekstas[:9000]}

GRIEŽTA TAISYKLĖ: Ištrauk TIK tas kainas (€/kWh), kurios yra AIŠKIAI IR TIKSLIAI nurodytos pateiktame tekste. Jei tekste kurio nors tinklo kainos nėra, palik ją tuščią (null). Niekada nespėliok ir nenaudok vidurkių! Taip pat apžvalgoje nenaudok programavimo žodžių („null“, „None“).

Grąžink JSON objektą su šiais raktais:
- "tariffs": objektas, kur raktas yra tikslus operatoriaus pavadinimas ("Ignitis ON", "Eleport", "Elinta Charge", "Inbalance grid", "Enefit Volt", "Lidl", "Ionity", "Tesla Supercharger", "Circle K", "Neste", "Virta"), o reikšmė {{"dc": 0.49, "ac": 0.37, "source_url": "https://..."}} (arba null vietoj skaičiaus, jei kainos tekste nėra; į source_url įrašyk tikrą nuorodą iš teksto).
- "summary_dc": 2 sakinių apžvalga vairuotojams apie šiuo metu žinomas greitojo DC įkrovimo kainas Lietuvoje.
- "summary_ac": 2 sakinių apžvalga vairuotojams apie šiuo metu žinomas lėtesnio AC įkrovimo kainas Lietuvoje."""
    try:
        di_ats = siusti_groq(promptas, max_tokens=2000)
        return {
            "tariffs": di_ats.get("tariffs") or {},
            "summary_dc": di_ats.get("summary_dc", "Greitojo DC įkrovimo kainų suvestinė atnaujinta pagal oficialius operatorių duomenis."),
            "summary_ac": di_ats.get("summary_ac", "Lėtesnio AC įkrovimo kainų suvestinė atnaujinta pagal oficialius operatorių duomenis.")
        }
    except Exception as e:
        print("Nepavyko gauti DI tarifų analizės:", e)
        return {
            "tariffs": {},
            "summary_dc": "Greitojo DC įkrovimo stotelių duomenys atnaujinti.",
            "summary_ac": "Lėtesnio AC įkrovimo stotelių duomenys atnaujinti."
        }
