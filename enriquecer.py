import json
import os
import requests

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama3-8b-8192"

def get_api_key():
    key = os.environ.get("GROQ_API_KEY", "")
    if not key:
        raise ValueError("GROQ_API_KEY no encontrada.")
    return key

def evaluar_grupo(titulos, key):
    prompt = f"""Sos un analista de medios argentinos experto en detectar desinformación y manipulación mediática.

Te doy titulares sobre el mismo tema de distintos medios:
{chr(10).join(f'- {t}' for t in titulos)}

Analizá y respondé SOLO con un JSON exactamente así, sin texto extra:
{{
  "relevancia": <número del 1 al 10, donde 10 es máxima importancia pública>,
  "tema": "<una de: Política, Economía, Judicial, Seguridad, Internacional, Sociedad, Cultura, Deportes, General>",
  "resumen": "<una oración de máximo 15 palabras describiendo de qué trata>",
  "controversia": <true si hay contradicción evidente entre los titulares>,
  "manipulacion": <true si la noticia parece usarse para instalar una narrativa, desviar atención, generar miedo o indignación con fines políticos, aunque el tema sea aparentemente mundano>
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
        texto = texto.replace("```json", "").replace("```", "").strip()
        return json.loads(texto)
    except Exception as e:
        return {"relevancia": 5, "tema": "General", "resumen": "", "controversia": False, "manipulacion": False}

def enriquecer_grupos():
    print("\n=== Enriqueciendo grupos con Groq ===")

    with open("grupos.json", encoding="utf-8") as f:
        grupos = json.load(f)

    key = get_api_key()
    total = len(grupos)

    for i, g in enumerate(grupos):
        titulos = [a["titulo"] for a in g.get("articulos", [])]
        if not titulos:
            continue

        resultado = evaluar_grupo(titulos, key)
        g["relevancia_ia"] = resultado.get("relevancia", 5)
        g["tema"] = resultado.get("tema", "General")
        g["resumen"] = resultado.get("resumen", "")
        g["controversia"] = resultado.get("controversia", False)
        g["manipulacion"] = resultado.get("manipulacion", False)

        flags = []
        if resultado.get("controversia"): flags.append("⚡ contradicción")
        if resultado.get("manipulacion"): flags.append("⚠️ manipulación")
        flags_str = " ".join(flags)
        print(f"  [{i+1}/{total}] ({resultado.get('relevancia','-')}/10) [{resultado.get('tema','')}] {g.get('resumen') or titulos[0][:55]} {flags_str}")

    with open("grupos.json", "w", encoding="utf-8") as f:
        json.dump(grupos, f, ensure_ascii=False, indent=2)

    print(f"\nListo. {total} grupos enriquecidos.")

if __name__ == "__main__":
    enriquecer_grupos()
