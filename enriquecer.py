import json
import os
import requests
from urllib.parse import urlparse

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"

TEMAS_VALIDOS = {"Política", "Economía", "Economía Internacional", "Judicial", "Seguridad", "Internacional", "Sociedad", "Cultura", "Deportes", "General"}

URL_CATEGORIAS = {
    "politica": "Política", "economia": "Economía", "economic": "Economía",
    "judicial": "Judicial", "tribunales": "Judicial", "justicia": "Judicial",
    "seguridad": "Seguridad", "policial": "Seguridad", "policiales": "Seguridad",
    "internacional": "Internacional", "mundo": "Internacional",
    "sociedad": "Sociedad", "salud": "Sociedad", "ciencia": "Sociedad",
    "cultura": "Cultura", "espectaculos": "Cultura", "entretenimiento": "Cultura",
    "deportes": "Deportes", "futbol": "Deportes", "deporte": "Deportes",
}

DOMINIOS_ARGENTINOS = [
    "infobae.com", "lanacion.com.ar", "clarin.com", "perfil.com",
    "ambito.com", "cronista.com", "pagina12.com.ar", "eldestapeweb.com",
    "tiempoar.com.ar"
]

# Palabras que indican que la noticia es de otro país y no Argentina
PAISES_EXTRANJEROS = [
    "perú", "peru", "colombia", "venezuela", "chile", "brasil", "uruguay",
    "bolivia", "paraguay", "ecuador", "méxico", "mexico", "cuba", "españa",
    "francia", "alemania", "italia", "rusia", "ucrania", "israel", "palestina",
    "china", "japon", "japón", "india", "corea", "eeuu", "estados unidos",
    "cdmx", "ciudad de méxico", "bogotá", "bogota", "lima", "caracas",
    "santiago de chile", "baja california", "vitarte",
]

# Excepciones — palabras que hacen que la noticia sea relevante para Argentina
CONTEXTO_ARGENTINO = [
    "argentina", "argentino", "argentinos", "argentinas",
    "milei", "kirchner", "macri", "massa", "bullrich",
    "fmi", "reservas", "dólar", "peso argentino",
    "banco central", "bcra", "conicet",
]

# Palabras de economía internacional relevante para Argentina
PALABRAS_ECO_INTL = [
    "wall street", "nasdaq", "dow jones", "fed", "reserva federal",
    "banco mundial", "fmi", "petróleo", "oro", "bitcoin", "crypto",
    "aranceles", "trump", "comercio mundial", "mercados globales",
]

def es_noticia_extranjera(titulo):
    t = titulo.lower()
    # Si menciona explícitamente Argentina o contexto local, no es extranjera
    if any(c in t for c in CONTEXTO_ARGENTINO):
        return False
    # Si menciona un país extranjero, es extranjera
    return any(p in t for p in PAISES_EXTRANJEROS)

def es_economica_internacional(titulo):
    t = titulo.lower()
    return any(p in t for p in PALABRAS_ECO_INTL)

def es_dominio_argentino(url):
    if not url:
        return True
    try:
        domain = urlparse(url).netloc.lower().replace("www.", "")
        return any(d in domain for d in DOMINIOS_ARGENTINOS)
    except:
        return True

def tema_desde_url(url):
    if not url:
        return None
    try:
        path = urlparse(url).path.lower()
        partes = [p for p in path.split("/") if p]
        for parte in partes:
            for keyword, tema in URL_CATEGORIAS.items():
                if keyword in parte:
                    return tema
    except:
        pass
    return None

def tema_desde_groq(titulo, key):
    prompt = f'Categoría de esta noticia argentina: "{titulo}"\nOpciones: Política, Economía, Judicial, Seguridad, Sociedad, Cultura, Deportes, General\nRespondé solo con una palabra.'
    try:
        r = requests.post(
            GROQ_API_URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
                "max_tokens": 5,
            },
            timeout=10
        )
        r.raise_for_status()
        respuesta = r.json()["choices"][0]["message"]["content"].strip()
        for t in TEMAS_VALIDOS:
            if t.lower() in respuesta.lower():
                return t
    except:
        pass
    return "General"

def enriquecer_grupos():
    print("\n=== Clasificando grupos por tema ===")

    with open("grupos.json", encoding="utf-8") as f:
        grupos = json.load(f)

    key = os.environ.get("GROQ_API_KEY", "")
    if not key:
        print("ADVERTENCIA: GROQ_API_KEY no encontrada. Solo se usará clasificación por URL.")

    desde_url = 0
    desde_groq = 0
    descartadas = 0
    total = len(grupos)

    for i, g in enumerate(grupos):
        arts = g.get("articulos", [])
        if not arts:
            g["tema"] = "General"
            continue

        primer_link = arts[0].get("link", "")
        titulo = arts[0]["titulo"]

        # Detectar si es de dominio extranjero
        if not es_dominio_argentino(primer_link):
            if es_economica_internacional(titulo):
                g["tema"] = "Economía Internacional"
                print(f"  [{i+1}/{total}] [INTL-ECO] {titulo[:60]}")
            else:
                g["tema"] = "Descartar"
                descartadas += 1
                print(f"  [{i+1}/{total}] [DESCARTA] {titulo[:60]}")
            continue

        # Detectar si la noticia habla de otro país por el título
        if es_noticia_extranjera(titulo):
            if es_economica_internacional(titulo):
                g["tema"] = "Economía Internacional"
                print(f"  [{i+1}/{total}] [INTL-ECO] {titulo[:60]}")
            else:
                g["tema"] = "Descartar"
                descartadas += 1
                print(f"  [{i+1}/{total}] [DESCARTA] {titulo[:60]}")
            continue

        # Intentar desde URL primero
        tema = None
        for art in arts:
            tema = tema_desde_url(art.get("link", ""))
            if tema:
                desde_url += 1
                break

        # Fallback a Groq
        if not tema and key:
            tema = tema_desde_groq(titulo, key)
            desde_groq += 1
        elif not tema:
            tema = "General"

        g["tema"] = tema
        print(f"  [{i+1}/{total}] [{'URL' if tema_desde_url(primer_link) else 'IA '}] [{tema}] {titulo[:60]}")

    with open("grupos.json", "w", encoding="utf-8") as f:
        json.dump(grupos, f, ensure_ascii=False, indent=2)

    print(f"\nListo. {total} grupos clasificados.")
    print(f"  Por URL: {desde_url} | Por Groq: {desde_groq} | Descartadas: {descartadas}")

if __name__ == "__main__":
    enriquecer_grupos()
