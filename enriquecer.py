import json
import os
import requests
from urllib.parse import urlparse

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"

TEMAS_VALIDOS = {"Política", "Economía", "Judicial", "Seguridad", "Internacional", "Sociedad", "Cultura", "Deportes", "General"}

# Mapeo de secciones de URL por medio
URL_CATEGORIAS = {
    "politica": "Política", "economia": "Economía", "economic": "Economía",
    "judicial": "Judicial", "tribunales": "Judicial", "justicia": "Judicial",
    "seguridad": "Seguridad", "policial": "Seguridad", "policiales": "Seguridad",
    "internacional": "Internacional", "mundo": "Internacional",
    "sociedad": "Sociedad", "salud": "Sociedad", "ciencia": "Sociedad",
    "cultura": "Cultura", "espectaculos": "Cultura", "entretenimiento": "Cultura",
    "deportes": "Deportes", "futbol": "Deportes", "deporte": "Deportes",
}

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
    prompt = f'Categoría de esta noticia argentina: "{titulo}"\nOpciones: Política, Economía, Judicial, Seguridad, Internacional, Sociedad, Cultura, Deportes, General\nRespondé solo con una palabra.'

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
    total = len(grupos)

    for i, g in enumerate(grupos):
        arts = g.get("articulos", [])
        if not arts:
            g["tema"] = "General"
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
            tema = tema_desde_groq(arts[0]["titulo"], key)
            desde_groq += 1
        elif not tema:
            tema = "General"

        g["tema"] = tema
        print(f"  [{i+1}/{total}] [{'URL' if tema_desde_url(arts[0].get('link','')) else 'IA'}] [{tema}] {arts[0]['titulo'][:60]}")

    with open("grupos.json", "w", encoding="utf-8") as f:
        json.dump(grupos, f, ensure_ascii=False, indent=2)

    print(f"\nListo. {total} grupos clasificados ({desde_url} por URL, {desde_groq} por Groq).")

if __name__ == "__main__":
    enriquecer_grupos()
