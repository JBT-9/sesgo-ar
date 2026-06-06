import feedparser
import requests
import json
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9",
}

TENDENCIA_LABEL = {
    "K": "Kirchnerista / progresista",
    "C": "Centro / independiente",
    "L": "Liberal / PRO / libertario",
}

MEDIOS_RSS = [
    {"nombre": "Infobae",   "rss": "https://www.infobae.com/arc/outboundfeeds/rss/",    "tendencia": "L"},
    {"nombre": "La Nación", "rss": "https://www.lanacion.com.ar/arc/outboundfeeds/rss/","tendencia": "L"},
    {"nombre": "Clarín",    "rss": "https://www.clarin.com/rss/lo-ultimo/",             "tendencia": "C"},
    {"nombre": "Perfil",    "rss": "https://www.perfil.com/feed",                       "tendencia": "C"},
]

MEDIOS_SCRAPE = [
    {"nombre": "Página 12",        "url": "https://www.pagina12.com.ar/",  "selector": "h2, h3", "tendencia": "K"},
    {"nombre": "El Destape",       "url": "https://www.eldestapeweb.com/", "selector": "h2, h3", "tendencia": "K"},
    {"nombre": "Tiempo Argentino", "url": "https://www.tiempoar.com.ar/",  "selector": "h2, h3", "tendencia": "K"},
    {"nombre": "Ámbito",           "url": "https://www.ambito.com/",       "selector": "h2, h3", "tendencia": "C"},
    {"nombre": "El Cronista",      "url": "https://www.cronista.com/",     "selector": "h2, h3", "tendencia": "C"},
]

SPAM_EXACTO = {
    "cultura y espectáculos", "política y economía", "sociedad", "deportes",
    "economía", "política", "internacional", "seguridad", "judicial",
    "últimas noticias", "más noticias", "seguimiento minuto a minuto",
    "tiempoargentino", "sumate a la comunidad de ámbito", "finanzas y economía",
    "idea management", "martín fierro", "lanzamientos", "inauguración",
    "opinión", "atención", "documentos", "medida", "inversión", "inversiones",
}

SPAM_PREFIJOS = ["por redacción", "por ", "foto:", "video:", "canal e", "mirá en vivo", "seguí en vivo", "en vivo |"]
SPAM_PALABRAS = ["quiniela", "casino", "ruleta", "poker", "slot", "apuesta", "suscribite", "sumate", "newsletter"]

def es_spam(titulo):
    if not titulo or len(titulo) < 20:
        return True
    if any(ord(c) > 1000 for c in titulo):
        return True
    t = titulo.lower().strip()
    if t in SPAM_EXACTO:
        return True
    if any(t.startswith(p) for p in SPAM_PREFIJOS):
        return True
    if any(p in t for p in SPAM_PALABRAS):
        return True
    if t.endswith(".") and len(titulo.split()) <= 3:
        return True
    if titulo == titulo.upper() and len(titulo) > 5:
        return True
    return False

def obtener_imagen(url):
    if not url:
        return ""
    try:
        r = requests.get(url, headers=HEADERS, timeout=6)
        soup = BeautifulSoup(r.content, "html.parser")
        og = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "og:image"})
        if og and og.get("content"):
            return og["content"]
    except:
        pass
    return ""

def fetch_rss(medio):
    try:
        r = requests.get(medio["rss"], headers=HEADERS, timeout=10)
        r.raise_for_status()
        feed = feedparser.parse(r.content)
        articulos = []
        for entry in feed.entries[:50]:
            titulo = entry.get("title", "").strip()
            if es_spam(titulo):
                continue
            link = entry.get("link", "")
            imagen = ""
            if hasattr(entry, "media_content") and entry.media_content:
                imagen = entry.media_content[0].get("url", "")
            if not imagen and hasattr(entry, "enclosures") and entry.enclosures:
                imagen = entry.enclosures[0].get("href", "")
            if not imagen and link:
                imagen = obtener_imagen(link)
            articulos.append({
                "titulo": titulo,
                "link": link,
                "imagen": imagen,
                "publicado": entry.get("published", ""),
                "medio": medio["nombre"],
                "tendencia": medio["tendencia"],
            })
        print(f"  RSS    {medio['nombre']:20s} — {len(articulos)} artículos")
        return articulos
    except Exception as e:
        print(f"  ERR    {medio['nombre']:20s} — {e}")
        return []

def fetch_scrape(medio):
    try:
        r = requests.get(medio["url"], headers=HEADERS, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "html.parser")
        vistos = set()
        articulos = []
        for el in soup.select(medio["selector"]):
            a = el.find("a") or el.find_parent("a")
            if not a or not a.get("href"):
                continue
            titulo = el.get_text(strip=True)
            if es_spam(titulo) or titulo in vistos:
                continue
            vistos.add(titulo)
            href = a["href"]
            link = href if href.startswith("http") else medio["url"].rstrip("/") + href
            if link.rstrip("/") == medio["url"].rstrip("/"):
                continue
            if any(link.endswith(s) for s in ["/", "#", "javascript:void(0)"]):
                continue
            imagen = obtener_imagen(link)
            articulos.append({
                "titulo": titulo,
                "link": link,
                "imagen": imagen,
                "publicado": "",
                "medio": medio["nombre"],
                "tendencia": medio["tendencia"],
            })
            if len(articulos) >= 30:
                break
        print(f"  SCRAPE {medio['nombre']:20s} — {len(articulos)} artículos")
        return articulos
    except Exception as e:
        print(f"  ERR    {medio['nombre']:20s} — {e}")
        return []

def cargar_historial():
    try:
        with open("historial.json", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def guardar_historial(historial):
    with open("historial.json", "w", encoding="utf-8") as f:
        json.dump(historial, f, ensure_ascii=False, indent=2)

def main():
    print("\n=== Scraper Sesgo AR ===")
    print(f"Corriendo: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("(Con imágenes — puede tardar unos minutos)\n")

    # Traer noticias nuevas
    nuevas = []
    print("-- Medios con RSS --")
    for medio in MEDIOS_RSS:
        nuevas.extend(fetch_rss(medio))
    print("\n-- Medios sin RSS (scraping directo) --")
    for medio in MEDIOS_SCRAPE:
        nuevas.extend(fetch_scrape(medio))

    # Cargar historial del día
    historial = cargar_historial()

    # Limpiar historial de más de 24 horas
    ahora = datetime.now()
    historial = [a for a in historial if
        (ahora - datetime.fromisoformat(a.get("scrapeado_en", ahora.isoformat()))).total_seconds() < 86400
    ]

    # Agregar solo las noticias nuevas (por link)
    links_existentes = {a["link"] for a in historial if a.get("link")}
    agregadas = 0
    for art in nuevas:
        if art.get("link") and art["link"] not in links_existentes:
            art["scrapeado_en"] = ahora.isoformat()
            historial.append(art)
            links_existentes.add(art["link"])
            agregadas += 1

    guardar_historial(historial)

    # noticias.json = todas las del historial (últimas 24hs)
    output = {
        "timestamp": ahora.isoformat(),
        "total": len(historial),
        "por_tendencia": {
            "K": len([a for a in historial if a["tendencia"] == "K"]),
            "C": len([a for a in historial if a["tendencia"] == "C"]),
            "L": len([a for a in historial if a["tendencia"] == "L"]),
        },
        "articulos": historial,
    }

    with open("noticias.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nNuevas: {agregadas} | Total últimas 24hs: {len(historial)}")
    for t, label in TENDENCIA_LABEL.items():
        print(f"  {t} ({label}): {output['por_tendencia'][t]}")

if __name__ == "__main__":
    main()
