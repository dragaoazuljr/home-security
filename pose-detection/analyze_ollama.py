import os
import json
import base64
import requests

# Configurações
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://host.docker.internal:11434/api/generate")
MODEL = os.environ.get("OLLAMA_MODEL", "gemma3:4b")
SNAPSHOT_DIR = os.environ.get("SNAPSHOT_DIR", "/app/snapshots/")
OUTPUT_FILE = os.environ.get("OUTPUT_FILE", "/app/ollama_result.json")

PROMPT = """
Há pessoas na foto? Quantas? Estão caídas no chão ou em potencial situação de perigo? 
Avalie a situação com um dos seguintes status:  
   * 🔴 Alto risco (queda clara ou situação perigosa, pessoa caída no chão, tentando se segurar em algo para levantar),
   * 🟠 Risco moderado (possível queda, desequilíbrio, agressão),
   * 🟢 Sem risco aparente (idosos de pé ou sentados, em situações de segurança.).
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


def load_previous_report():
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def generate_global_report(previous_report, current_results):
    old_global = previous_report.get("__relatorio_global__", "Nenhum relatório anterior disponível.")

    analyses_text = "\n".join(
        f"{img}: {analysis}" for img, analysis in current_results.items()
    )

    prompt = f"""
Relatório global anterior:
{old_global}

Novas análises individuais:
{analyses_text}

Tarefas para o relatório global:
1. Compare a situação atual com a anterior.
2. Destaque mudanças (número de pessoas, posições, riscos).
3. Informe se houve aumento ou redução de risco.
4. Dê uma visão consolidada da situação atual, com risco geral.
5. Classifique o risco geral da casa: 🔴 Alto, 🟠 Moderado ou 🟢 Baixo.

Responda em formato de relatório claro, objetivo e organizado.
"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False
        },
        timeout=180
    )

    if response.status_code != 200:
        raise RuntimeError(f"Ollama retornou {response.status_code}: {response.text}")

    return response.json().get("response", "").strip()


def main():
    results = {}
    previous_report = load_previous_report()

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

    # Gera relatório global com comparação
    print("\n📊 Gerando relatório global...")
    try:
        global_report = generate_global_report(previous_report, results)
        results["__relatorio_global__"] = global_report
        print(f"\n📑 Relatório atualizado:\n{global_report}\n")
    except Exception as e:
        print(f"❌ Erro ao gerar relatório global: {e}")

    # Salva no JSON final
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n📂 Resultados salvos em {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
