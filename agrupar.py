from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import json
import numpy as np

UMBRAL = 0.75

TODOS_LOS_MEDIOS = [
    "Infobae", "La Nación", "Clarín", "Perfil",
    "Ámbito", "El Cronista", "Página 12", "El Destape", "Tiempo Argentino"
]

def cargar_noticias():
    with open("noticias.json", encoding="utf-8") as f:
        data = json.load(f)
    return data["articulos"]

def agrupar(articulos):
    print("Cargando modelo de embeddings...")
    modelo = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    titulos = [a["titulo"] for a in articulos]
    print(f"Calculando embeddings para {len(titulos)} artículos...")
    embeddings = modelo.encode(titulos, show_progress_bar=True)
    print("Agrupando por similitud semántica...")
    similitudes = cosine_similarity(embeddings)
    asignado = [False] * len(articulos)
    grupos = []
    for i in range(len(articulos)):
        if asignado[i]:
            continue
        grupo = [i]
        asignado[i] = True
        for j in range(i + 1, len(articulos)):
            if not asignado[j] and similitudes[i][j] >= UMBRAL:
                medios_en_grupo = {articulos[k]["medio"] for k in grupo}
                if articulos[j]["medio"] not in medios_en_grupo:
                    grupo.append(j)
                    asignado[j] = True
        grupos.append(grupo)
    return grupos

def main():
    articulos = cargar_noticias()
    medios_presentes = {a["medio"] for a in articulos}
    grupos = agrupar(articulos)

    resultado = []
    for grupo in grupos:
        items = [articulos[i] for i in grupo]
        tendencias = {a["tendencia"] for a in items}
        medios_grupo = [a["medio"] for a in items]

        # Ausentes: medios que sí scrapeamos pero no cubrieron esta noticia
        ausentes = [m for m in TODOS_LOS_MEDIOS if m in medios_presentes and m not in medios_grupo]

        resultado.append({
            "titulo_representativo": items[0]["titulo"],
            "cantidad_articulos": len(items),
            "medios": medios_grupo,
            "tendencias_cubren": sorted(tendencias),
            "blind_spot": ausentes,
            "articulos": items,
        })

    resultado.sort(key=lambda x: x["cantidad_articulos"], reverse=True)

    with open("grupos.json", "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    multi = [g for g in resultado if g["cantidad_articulos"] > 1]
    con_blind_spot = [g for g in multi if g["blind_spot"]]

    print(f"\n=== Resultado ===")
    print(f"Total grupos: {len(resultado)}")
    print(f"Noticias cubiertas por más de un medio: {len(multi)}")
    print(f"Noticias con blind spot: {len(con_blind_spot)}")

    print(f"\n--- Top 5 noticias más cubiertas ---")
    for g in resultado[:5]:
        bs = f"  [ausente en: {', '.join(g['blind_spot'][:3])}{'...' if len(g['blind_spot'])>3 else ''}]" if g["blind_spot"] else ""
        print(f"\n  {g['titulo_representativo'][:70]}")
        print(f"  Medios: {', '.join(g['medios'])}{bs}")

    print(f"\nGrupos guardados en grupos.json")

if __name__ == "__main__":
    main()
