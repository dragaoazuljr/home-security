import os
import json
import base64
import requests
import telegramify_markdown
import concurrent.futures

from telegram import Bot

# --------------- Configurações ----------------
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://host.docker.internal:11434/api/generate")
MODEL = os.environ.get("OLLAMA_MODEL", "gemma3:4b")
SNAPSHOT_DIR = os.environ.get("SNAPSHOT_DIR", "/app/snapshots")
OUTPUT_FILE = os.environ.get("OUTPUT_FILE", "/app/history.json")

# Telegram
BOT_TOKEN = os.environ.get("BOT_TOKEN", "token")
CHAT_ID = os.environ.get("CHAT_ID", "chat")
bot = Bot(token=BOT_TOKEN)

VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

# Prompt Ollama
# PROMPT = """
# Você é um sistema de análise de imagens especializado em segurança doméstica para idosos.
# Sua tarefa é:
# 
# 1. Identificar pessoas idosas na imagem fornecida.
# 2. Verificar se há indícios de situações de perigo:
#    - queda no chão
#    - tropeço
#    - dificuldade para se levantar
#    - postura corporal anormal
# 3. Classificar risco: 🔴 Alto, 🟠 Moderado, 🟢 Sem risco aparente
# 4. Explicar brevemente a razão da classificação
# 
# Responda no formato do Telegram MarkdownV2 e seguindo o padrão:
# 
# - Situação: [descrição]
# - Classificação de risco: [🟢 / 🟠 / 🔴]
# - Justificativa: [curta]
# """

PROMPT = """
Há pessoas na foto? Quantas? Estão caídas no chão ou em potencial situação de perigo? 
Avalie a situação com um dos seguintes status:  
   * 🔴 Alto risco (queda clara ou situação perigosa, pessoa caída no chão, tentando se segurar em algo para levantar),
   * 🟠 Risco moderado (possível queda, desequilíbrio, agressão),
   * 🟢 Sem risco aparente (idosos de pé ou sentados, em situações de segurança.).

Responda no formato do Telegram MarkdownV2 e seguindo o padrão:

- Situação: [descrição]
- Classificação de risco: [🟢 / 🟠 / 🔴]
- Justificativa: [curta]
"""

# ---------------- Funções -------------------

def analyze_image(image_path):
    with open(image_path, "rb") as f:
        image_bytes = f.read()
        image_b64 = base64.b64encode(image_bytes).decode()

    response = requests.post(
        OLLAMA_URL,
        json={"model": MODEL, "prompt": PROMPT, "images": [image_b64], "stream": False},
        timeout=120
    )
    if response.status_code != 200:
        raise RuntimeError(f"Ollama retornou {response.status_code}: {response.text}")
    return response.json().get("response", "").strip()


def load_history():
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_history(history):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

def generate_global_report(previous_report, current_results):
    old_global = previous_report.get("__global_report__", "Nenhum relatório anterior.")
    analyses_text = "\n".join(f"{img}: {analysis}" for img, analysis in current_results.items())
    
    prompt = f"""
Relatório anterior:
{old_global}

Novas análises:
{analyses_text}

Tarefas:
1. Compare situação atual com anterior, mas não mencione o risco da situação anterior
2. Destaque mudanças
3. Informe aumento/redução de risco
4. Dê visão consolidada
5. Classifique risco geral da casa: 🔴 / 🟠 / 🟢

Responda de forma clara, objetiva, organizada e seja breve.
"""
    response = requests.post(
        OLLAMA_URL,
        json={"model": MODEL, "prompt": prompt, "stream": False},
        timeout=180
    )
    if response.status_code != 200:
        raise RuntimeError(f"Ollama retornou {response.status_code}: {response.text}")
    return response.json().get("response", "").strip() 


def send_telegram(report_text, image_paths, results):
    try:
        # envia relatório

        disable_notification = True

        # ativa notificação se no relatorio tiver 🔴
        if ' 🔴 ' in report_text:
            disable_notification = False

        converted = telegramify_markdown.markdownify(
            report_text,
            max_line_length=None,  # If you want to change the max line length for links, images, set it to the desired value.
            normalize_whitespace=False
        )

        bot.send_message(chat_id=CHAT_ID, text=converted, parse_mode='MarkdownV2', disable_notification=disable_notification)
        # envia fotos com legenda de análise
        for img_path in image_paths:
            img_name = os.path.basename(img_path)
            caption = results.get(img_name, "")
            with open(img_path, "rb") as f:
                bot.send_photo(chat_id=CHAT_ID, photo=f, caption=caption, parse_mode='Markdown', disable_notification=True)
        print("✅ Relatório e fotos enviados ao Telegram")
    except Exception as e:
        print(f"❌ Erro ao enviar Telegram: {e}")


# ---------------- Main -------------------
def main():
    history = load_history()
    results = {}
    image_paths = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_img = {}
        for img_file in os.listdir(SNAPSHOT_DIR):
            _, ext = os.path.splitext(img_file.lower())
            if ext not in VALID_EXTENSIONS:
                continue
            img_path = os.path.join(SNAPSHOT_DIR, img_file)
            image_paths.append(img_path)
            print(f"🔍 Analisando {img_file}...")
            future = executor.submit(analyze_image, img_path)
            future_to_img[future] = img_file
        for future in concurrent.futures.as_completed(future_to_img):
            img_file = future_to_img[future]
            try:
                analysis = future.result()
                results[img_file] = analysis
                print(f"✅ {img_file} -> {analysis}")
            except Exception as e:
                print(f"❌ Erro ao analisar {img_file}: {e}")

    print("📊 Gerando relatório global...")
    try:
        global_report = generate_global_report(history, results)
        results["__global_report__"] = global_report
        print(global_report)
    except Exception as e:
        global_report = "Erro ao gerar relatório global"
        print(f"❌ {e}")

    save_history(results)
    send_telegram(global_report, image_paths, results)


if __name__ == "__main__":
    main()

