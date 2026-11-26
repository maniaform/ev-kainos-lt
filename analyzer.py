import os
import re
import json
import requests

GROQ_BASE = "https://" + "api.groq" + ".com/openai/v1"

def rasti_veikianti_groq_modeli(api_key):
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        r = requests.get(f"{GROQ_BASE}/models", headers=headers, timeout=10)
        if r.ok:
            modeliai = [m["id"] for m in r.json().get("data", []) if "whisper" not in m["id"] and "guard" not in m["id"]]
            for pageidaujamas in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "openai/gpt-oss-120b", "qwen/qwen3-32b"]:
                if pageidaujamas in modeliai:
                    return pageidaujamas
            if modeliai:
                return modeliai[0]
    except Exception:
        pass
    return "llama-3.1-8b-instant"

def siusti_groq(promptas, max_tokens=2000):
    api_key = (os.environ.get("GROQ_API_KEY") or "").strip()
    if not api_key:
        raise ValueError("Nerastas GROQ_API_KEY raktas!")

    modelis = rasti_veikianti_groq_modeli(api_key)
    print(f"Naudojamas Groq DI modelis: {modelis}")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": modelis,
        "messages": [
            {
                "role": "system",
                "content": "Esi griežtas faktų tikrintojas ir tikslus Lietuvos elektromobilių rinkos analitikas. Grąžink TIK gryną JSON objektą. Visus tekstus (summary_dc ir summary_ac) rašyk TIK taisyklinga lietuvių kalba! Niekada neišsigalvok ir nespėliok kainų, jei jų nėra tekste."
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
    res = requests.post(f"{GROQ_BASE}/chat/completions", headers=headers, json=payload, timeout=30)
    res.raise_for_status()
    return json.loads(res.json()["choices"][0]["message"]["content"])

def nustatyti_operatoriu_tarifus(paieskos_tekstas, dabar_str):
    tarifai = {}

    # Tiesioginis Eleport Lietuvos kainų ištraukimas iš oficialaus bloko, jei jis nuskaitytas
    eleport_match = re.search(r'=== OFICIALUS PUSLAPIS \(LIETUVA\): Eleport.*?===\n(.*)', paieskos_tekstas)
    if eleport_match:
        el_txt = eleport_match.group(1)
        ac_m = re.search(r'AC.*?(\d+[.,]\d+)\s*€', el_txt)
        dc_m = re.search(r'DC.*?(\d+[.,]\d+)\s*€', el_txt)
        if ac_m or dc_m:
            tarifai["Eleport"] = {
                "ac": round(float(ac_m.group(1).replace(',', '.')), 2) if ac_m else None,
                "dc": round(float(dc_m.group(1).replace(',', '.')), 2) if dc_m else None,
                "source_url": "https://eleport.com"
            }

    promptas = f"""Išanalizuok šiuos duomenis iš oficialių operatorių puslapių ir paieškos apie EV įkrovimo kainas Lietuvoje ({dabar_str}):
{paieskos_tekstas[:9000]}

GRIEŽTA TAISYKLĖ: Ištrauk TIK tas kainas (€/kWh), kurios yra AIŠKIAI IR TIKSLIAI nurodytos pateiktame tekste. Jei tekste kurio nors tinklo kainos nėra, palik ją tuščią (null). Niekada nespėliok ir nenaudok vidurkių!

Grąžink JSON objektą su šiais raktais:
- "tariffs": objektas, kur raktas yra operatoriaus pavadinimas ("Ignitis ON", "Eleport", "Elinta Charge", "Inbalance grid", "Enefit Volt", "Lidl", "Ionity", "Tesla Supercharger", "Circle K", "Neste", "Virta"), o reikšmė {{"dc": 0.49, "ac": 0.37, "source_url": "https://..."}} (arba null vietoj skaičiaus, jei kainos tekste nėra).
- "summary_dc": 2 sakinių apžvalga vairuotojams apie šiuo metu žinomas greitojo DC įkrovimo kainas Lietuvoje.
- "summary_ac": 2 sakinių apžvalga vairuotojams apie šiuo metu žinomas lėtesnio AC įkrovimo kainas Lietuvoje."""

    try:
        di_ats = siusti_groq(promptas)
        di_tarifai = di_ats.get("tariffs") or {}
        for op, val in di_tarifai.items():
            if op not in tarifai and isinstance(val, dict):
                tarifai[op] = val
        return {
            "tariffs": tarifai,
            "summary_dc": di_ats.get("summary_dc", "Greitojo DC įkrovimo kainos atnaujintos pagal oficialius operatorių puslapius."),
            "summary_ac": di_ats.get("summary_ac", "Lėtesnio AC įkrovimo kainos atnaujintos pagal oficialius operatorių puslapius.")
        }
    except Exception as e:
        print("Nepavyko gauti DI tarifų analizės:", e)
        return {
            "tariffs": tarifai,
            "summary_dc": "Greitojo DC įkrovimo stotelių ir oficialių tarifų duomenys atnaujinti.",
            "summary_ac": "Lėtesnio AC įkrovimo stotelių ir oficialių tarifų duomenys atnaujinti."
        }
