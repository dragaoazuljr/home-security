import os
import json
import base64
import requests

# Configurações
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://host.docker.internal:11434/api/generate")
MODEL = os.environ.get("OLLAMA_MODEL", "gemma3:4b")
SNAPSHOT_DIR = os.environ.get("SNAPSHOT_DIR", "/app/snapshots/")
OUTPUT_FILE = os.environ.get("OUTPUT_FILE", "/app/gemma3_results.json")

PROMPT = """
Há pessoas na foto? Quantas? Estão caidas no chão ou em potencial situação de perigo? 
Avalie a situação com um dos seguintes status:  
   * 🔴 Alto risco (queda clara ou situação perigosa, pessoa caida no chão, tentando se segurar em algo para levantar),
   * 🟠 Risco moderado (possivel queda, desequilíbrio),
   * 🟢 Sem risco aparente (idosos de pé e estáveis).
"""

VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def analyze_image(image_path):
    with open(image_path, "rb") as f:
        image_bytes = f.read()
        image_b64 = base64.b64encode(image_bytes).decode()

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": PROMPT,
            "images": [image_b64],
            "stream": False
        },
        timeout=120
    )

    if response.status_code != 200:
        raise RuntimeError(f"Ollama retornou {response.status_code}: {response.text}")

    data = response.json()

    return data.get("response", "").strip()


def main():
    results = {}

    for img_file in os.listdir(SNAPSHOT_DIR):
        _, ext = os.path.splitext(img_file.lower())
        if ext not in VALID_EXTENSIONS:
            continue

        img_path = os.path.join(SNAPSHOT_DIR, img_file)
        print(f"🔍 Analisando {img_file} com {MODEL}...")

        try:
            analysis = analyze_image(img_path)
            results[img_file] = analysis
            print(f"✅ {img_file} -> {analysis}\n")
        except Exception as e:
            print(f"❌ Erro ao analisar {img_file}: {e}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n📂 Resultados salvos em {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
