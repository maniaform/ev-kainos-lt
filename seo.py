import os
import re

BASE_URL = "https://" + "ev-kainos-lt" + ".vercel.app"

def sukurti_slug(tekstas):
    p = tekstas.lower().strip()
    lt = {'ą': 'a', 'č': 'c', 'ę': 'e', 'ė': 'e', 'į': 'i', 'š': 's', 'ų': 'u', 'ū': 'u', 'ž': 'z'}
    for k, v in lt.items():
        p = p.replace(k, v)
    return re.sub(r'[^a-z0-9]+', '-', p).strip('-')

def formatuoti_kaina(val, is_free):
    if is_free or val == 0:
        return "0.00 € (Nemokama)"
    return f"{val:.2f} €/kWh" if isinstance(val, (int, float)) else "Tarifas programėlėje"

def generuoti_ev_seo(duomenys):
    os.makedirs("tinklai", exist_ok=True)
    os.makedirs("miestai", exist_ok=True)
    os.makedirs("keliai", exist_ok=True)
    sitemap_urls = [f"{BASE_URL}/"]

    # 1. OPERATORIŲ (TINKLŲ) SEO PUSLAPIAI
    for net in duomenys.get("networks", []):
        slug = net["id"]
        failo_kelias = f"tinklai/{slug}.html"
        pilnas_url = f"{BASE_URL}/{failo_kelias}"
        sitemap_urls.append(pilnas_url)

        eilutes = ""
        for s in net.get("stations", []):
            kaina_str = formatuoti_kaina(s.get("price"), s.get("is_free"))
            jungtys = ", ".join(s.get("connectors") or [])
            eilutes += f"<tr><td><strong>{s['city']}</strong></td><td>{s['address']}</td><td>{jungtys}</td><td><span class='kw-badge'>{s['power_kw']} kW</span></td><td class='mono' style='color:#059669;'>{kaina_str}</td></tr>"

        html = f"""<!DOCTYPE html>
<html lang="lt">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{net['name']} elektromobilių įkrovimo kainos (€/kWh) ir stotelės | EV kainos Lietuvoje</title>
    <meta name="description" content="Naujausios {net['name']} elektromobilių įkrovimo kainos (€/kWh), stotelių adresai, jungtys (CCS2, Type 2) ir galia iki {net.get('max_power_kw', 0)} kW. Iš viso {len(net.get('stations', []))} stotelės.">
    <link rel="canonical" href="{pilnas_url}">
    <link rel="stylesheet" href="../style.css">
</head>
<body>
    <header class="header">
        <div class="container header-inner">
            <a href="../index.html" style="text-decoration:none; color:white;"><div class="logo">EV kainos <span>Lietuvoje</span></div></a>
            <a href="../index.html" class="fuel-btn active" style="text-decoration:none;">← Visi operatoriai</a>
        </div>
    </header>
    <main class="container" style="padding-top: 32px; padding-bottom: 60px;">
        <h1 class="section-title" style="font-size: 1.75rem;">⚡ {net['name']} — elektromobilių įkrovimo stotelės ir kainos</h1>
        <p style="color: var(--text-muted); margin-bottom: 24px;">Atnaujinta: {duomenys['last_updated']} • Maksimali galia: iki {net.get('max_power_kw', 0)} kW • Stotelių skaičius: {len(net.get('stations', []))}</p>
        <div style="background: white; padding: 20px; border-radius: 16px; border: 1px solid var(--border-light); overflow-x:auto;">
            <table class="stations-table">
                <thead><tr><th>Miestas</th><th>Adresas</th><th>Jungtys</th><th>Galia</th><th>Kaina</th></tr></thead>
                <tbody>{eilutes}</tbody>
            </table>
        </div>
    </main>
</body>
</html>"""
        with open(failo_kelias, "w", encoding="utf-8") as f:
            f.write(html)

    # 2. MIESTŲ IR SAVIVALDYBIŲ SEO PUSLAPIAI
    miestu_stoteles = {}
    for net in duomenys.get("networks", []):
        for s in net.get("stations", []):
            miestas = (s.get("city") or "").strip()
            if miestas:
                miestu_stoteles.setdefault(miestas, []).append({**s, "operator": net["name"]})

    visu_miestu_nuorodos = []

    for miestas in sorted(miestu_stoteles.keys()):
        stotys = miestu_stoteles[miestas]
        m_slug = sukurti_slug(miestas)
        if not m_slug:
            continue
        m_kelias = f"miestai/{m_slug}.html"
        m_url = f"{BASE_URL}/{m_kelias}"
        sitemap_urls.append(m_url)
        visu_miestu_nuorodos.append(f'<a href="{m_kelias}" style="padding:6px 12px; background:white; border:1px solid var(--border-light); border-radius:8px; text-decoration:none; color:var(--text-main);">{miestas} ({len(stotys)})</a>')

        stotys.sort(key=lambda x: (x.get("price") if isinstance(x.get("price"), (int, float)) else 99, -(x.get("power_kw") or 0)))

        m_eilutes = ""
        for s in stotys:
            kaina_str = formatuoti_kaina(s.get("price"), s.get("is_free"))
            jungtys = ", ".join(s.get("connectors") or [])
            m_eilutes += f"<tr><td><strong>{s['operator']}</strong></td><td>{s['address']}</td><td>{jungtys}</td><td><span class='kw-badge'>{s['power_kw']} kW</span></td><td class='mono' style='color:#059669;'>{kaina_str}</td></tr>"

        m_html = f"""<!DOCTYPE html>
<html lang="lt">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Elektromobilių įkrovimo stotelės ir kainos: {miestas} (€/kWh, kW) | EV kainos Lietuvoje</title>
    <meta name="description" content="Visos elektromobilių įkrovimo stotelės vietovėje {miestas} ({len(stotys)} taškai). Patikrinkite kainas (€/kWh), jungčių tipus (CCS2, Type 2) ir galią (kW).">
    <link rel="canonical" href="{m_url}">
    <link rel="stylesheet" href="../style.css">
</head>
<body>
    <header class="header">
        <div class="container header-inner">
            <a href="../index.html" style="text-decoration:none; color:white;"><div class="logo">EV kainos <span>Lietuvoje</span></div></a>
            <a href="../index.html" class="fuel-btn active" style="text-decoration:none;">← Visos vietovės</a>
        </div>
    </header>
    <main class="container" style="padding-top: 32px; padding-bottom: 60px;">
        <h1 class="section-title" style="font-size: 1.75rem;">📍 Elektromobilių įkrovimo stotelės — {miestas}</h1>
        <p style="color: var(--text-muted); margin-bottom: 24px;">Atnaujinta: {duomenys['last_updated']} • Rasta stotelių: {len(stotys)}</p>
        <div style="background: white; padding: 20px; border-radius: 16px; border: 1px solid var(--border-light); overflow-x:auto;">
            <table class="stations-table">
                <thead><tr><th>Operatorius</th><th>Adresas</th><th>Jungtys</th><th>Galia</th><th>Kaina</th></tr></thead>
                <tbody>{m_eilutes}</tbody>
            </table>
        </div>
    </main>
</body>
</html>"""
        with open(m_kelias, "w", encoding="utf-8") as f:
            f.write(m_html)

    # 3. MAGISTRALINIŲ KELIŲ SEO PUSLAPIAI
    magistrales = [
        {"slug": "a1-vilnius-kaunas-klaipeda", "name": "Magistralė A1 (Vilnius – Kaunas – Klaipėda)", "raktazodziai": ["a1", "vilniaus pl", "kauno pl", "klaipėdos pl", "savanorių pr", "islandijos pl", "jakų"]},
        {"slug": "a2-vilnius-panevezys", "name": "Magistralė A2 (Vilnius – Ukmergė – Panevėžys)", "raktazodziai": ["a2", "ukmergės", "širvint"]},
        {"slug": "via-baltica-a5-a8-a10", "name": "Via Baltica (A5 / A8 / A10)", "raktazodziai": ["a5", "a8", "a10", "via baltica", "marijampol", "pasval", "kedain"]},
        {"slug": "a6-kaunas-zarasai", "name": "Kelias A6 (Kaunas – Utena – Zarasai)", "raktazodziai": ["a6", "jonav", "uten", "zaras"]},
        {"slug": "a11-siauliai-palanga", "name": "Kelias A11 (Šiauliai – Plungė – Palanga)", "raktazodziai": ["a11", "telš", "plung", "kreting", "palang"]}
    ]

    for kelias in magistrales:
        k_stotys = []
        for net in duomenys.get("networks", []):
            for s in net.get("stations", []):
                pilnas_adr = f"{s.get('city', '')} {s.get('address', '')}".lower()
                if any(rz in pilnas_adr for rz in kelias["raktazodziai"]):
                    k_stotys.append({**s, "operator": net["name"]})

        if not k_stotys:
            continue

        k_kelias = f"keliai/{kelias['slug']}.html"
        k_url = f"{BASE_URL}/{k_kelias}"
        sitemap_urls.append(k_url)

        k_stotys.sort(key=lambda x: (x.get("price") if isinstance(x.get("price"), (int, float)) else 99, -(x.get("power_kw") or 0)))

        k_eilutes = ""
        for s in k_stotys:
            kaina_str = formatuoti_kaina(s.get("price"), s.get("is_free"))
            jungtys = ", ".join(s.get("connectors") or [])
            k_eilutes += f"<tr><td><strong>{s['operator']}</strong></td><td>{s['city']}</td><td>{s['address']}</td><td>{jungtys}</td><td><span class='kw-badge'>{s['power_kw']} kW</span></td><td class='mono' style='color:#059669;'>{kaina_str}</td></tr>"

        k_html = f"""<!DOCTYPE html>
<html lang="lt">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Elektromobilių įkrovimas kelyje: {kelias['name']} (€/kWh, kW) | EV kainos Lietuvoje</title>
    <meta name="description" content="Elektromobilių įkrovimo stotelės pakeliui: {kelias['name']}. Rasta {len(k_stotys)} įkrovimo taškų su nurodyta galia (kW) ir kainomis (€/kWh).">
    <link rel="canonical" href="{k_url}">
    <link rel="stylesheet" href="../style.css">
</head>
<body>
    <header class="header">
        <div class="container header-inner">
            <a href="../index.html" style="text-decoration:none; color:white;"><div class="logo">EV kainos <span>Lietuvoje</span></div></a>
            <a href="../index.html" class="fuel-btn active" style="text-decoration:none;">← Pagrindinis puslapis</a>
        </div>
    </header>
    <main class="container" style="padding-top: 32px; padding-bottom: 60px;">
        <h1 class="section-title" style="font-size: 1.75rem;">🛣️ Elektromobilių įkrovimas kelyje: {kelias['name']}</h1>
        <p style="color: var(--text-muted); margin-bottom: 24px;">Atnaujinta: {duomenys['last_updated']} • Rasta stotelių: {len(k_stotys)}</p>
        <div style="background: white; padding: 20px; border-radius: 16px; border: 1px solid var(--border-light); overflow-x:auto;">
            <table class="stations-table">
                <thead><tr><th>Operatorius</th><th>Miestas</th><th>Adresas</th><th>Jungtys</th><th>Galia</th><th>Kaina</th></tr></thead>
                <tbody>{k_eilutes}</tbody>
            </table>
        </div>
    </main>
</body>
</html>"""
        with open(k_kelias, "w", encoding="utf-8") as f:
            f.write(k_html)

    # 4. ATNAUJINAME NUORODAS PAGRINDINIAME INDEX.HTML
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            idx_html = f.read()
        start_tag = "<!-- SEO_EV_MIESTAI_START -->"
        end_tag = "<!-- SEO_EV_MIESTAI_END -->"
        if start_tag in idx_html and end_tag in idx_html:
            naujas_blokas = f"{start_tag}\n" + "\n".join(visu_miestu_nuorodos) + f"\n{end_tag}"
            idx_html = re.sub(f"{start_tag}.*?{end_tag}", naujas_blokas, idx_html, flags=re.DOTALL)
            with open("index.html", "w", encoding="utf-8") as f:
                f.write(idx_html)

    # 5. SITEMAP.XML IR ROBOTS.TXT
    sitemap_urls.append(f"{BASE_URL}/widget.html")
    ns = "http://" + "www.sitemaps.org/schemas/sitemap/0.9"
    xml = ['<?xml version="1.0" encoding="UTF-8"?>', f'<urlset xmlns="{ns}">']
    for u in sitemap_urls:
        xml.append(f"  <url><loc>{u}</loc></url>")
    xml.append("</urlset>")
    with open("sitemap.xml", "w", encoding="utf-8") as f:
        f.write("\n".join(xml))

    with open("robots.txt", "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}/sitemap.xml\n")
