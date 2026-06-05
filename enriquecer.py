import json
import os
import requests

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama3-8b-8192"

def get_api_key():
    key = os.environ.get("GROQ_API_KEY", "")
    if not key:
        raise ValueError("GROQ_API_KEY no encontrada. Corré: $env:GROQ_API_KEY='tu_key'")
    return key

def evaluar_grupo(titulos, key):
    """Manda los titulos de un grupo a Groq y pide relevancia + tema."""
    prompt = f"""Sos un analista de medios argentinos. Te doy titulares de noticias sobre el mismo tema publicados por distintos medios.

Titulares:
{chr(10).join(f'- {t}' for t in titulos)}

Respondé SOLO con un JSON con este formato exacto, sin texto extra:
{{
  "relevancia": <número del 1 al 10>,
  "tema": "<una de estas categorías: Política, Economía, Seguridad, Judicial, Internacional, Cultura, Deportes, Sociedad>",
  "resumen": "<una oración de máximo 15 palabras que describa de qué trata la noticia>",
  "controversia": <true o false, si hay contradicción evidente entre los titulares>
}}"""

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 200,
    }

    try:
        r = requests.post(GROQ_API_URL, headers=headers, json=body, timeout=15)
        r.raise_for_status()
        texto = r.json()["choices"][0]["message"]["content"].strip()
        # Limpiar posibles backticks
        texto = texto.replace("```json", "").replace("```", "").strip()
        return json.loads(texto)
    except Exception as e:
        return {"relevancia": 5, "tema": "General", "resumen": "", "controversia": False}

def enriquecer_grupos():
    print("\n=== Enriqueciendo grupos con Groq ===")

    with open("grupos.json", encoding="utf-8") as f:
        grupos = json.load(f)

    key = get_api_key()
    total = len(grupos)
    procesados = 0

    for i, g in enumerate(grupos):
        titulos = [a["titulo"] for a in g.get("articulos", [])]
        if not titulos:
            continue

        resultado = evaluar_grupo(titulos, key)
        g["relevancia_ia"] = resultado.get("relevancia", 5)
        g["tema"] = resultado.get("tema", "General")
        g["resumen"] = resultado.get("resumen", "")
        g["controversia"] = resultado.get("controversia", False)

        procesados += 1
        print(f"  [{procesados}/{total}] ({resultado.get('relevancia','-')}/10) {g['resumen'] or titulos[0][:60]}")

    # Guardar
    with open("grupos.json", "w", encoding="utf-8") as f:
        json.dump(grupos, f, ensure_ascii=False, indent=2)

    print(f"\nListo. {procesados} grupos enriquecidos.")

if __name__ == "__main__":
    enriquecer_grupos()
