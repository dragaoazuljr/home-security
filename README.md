# **Guia de Implementação Prática – Sistema de Monitoramento de Idosos**

---

## **1️⃣ Raspberry Pi Zero 2W – Subnet Router via Tailscale**

1. Atualizar e instalar Tailscale:

```bash
sudo apt update && sudo apt upgrade -y
curl -fsSL https://tailscale.com/install.sh | sh
```

2. Ativar Tailscale e anunciar a subnet da rede local (ex.: 192.168.1.0/24):

```bash
sudo tailscale up --advertise-routes=192.168.1.0/24
```

3. No painel Tailscale, autorizar o Pi Zero como **subnet router**.

4. Testar:

```bash
ping 192.168.1.X  # IP de uma câmera
```

✅ Deve responder.

---

## **2️⃣ Proxmox – Containers**

### **2.1 Container 1: Frigate (NVR / Dashboard)**

**Docker Compose básico**:

```yaml
version: "3.9"
services:
  frigate:
    image: blakeblackshear/frigate:stable
    privileged: true
    restart: unless-stopped
    ports:
      - "5000:5000"  # Dashboard
    volumes:
      - /etc/frigate/config.yml:/config/config.yml:ro
      - /mnt/frigate/clips:/media/frigate/clips
      - /mnt/frigate/recordings:/media/frigate/recordings
```

**Exemplo de `config.yml`**:

```yaml
cameras:
  sala:
    ffmpeg:
      inputs:
        - path: rtsp://192.168.1.101:554/stream
          roles:
            - detect
            - record
  cozinha:
    ffmpeg:
      inputs:
        - path: rtsp://192.168.1.102:554/stream
          roles:
            - detect
            - record
detect:
  width: 640
  height: 480
  fps: 5
```

* Ajuste `path` para os IPs locais via Tailscale.
* Frigate gera snapshots e gravações automaticamente.

---

### **2.2 Container 2: OpenPose / Analisador de Postura**

**Dockerfile básico** (OpenPose/MediaPipe em Python):

```dockerfile
FROM python:3.11-slim

RUN pip install opencv-python numpy mediapipe requests

WORKDIR /app
COPY analyze.py /app/analyze.py

CMD ["python", "analyze.py"]
```

**`analyze.py`** – pipeline básico:

```python
import cv2
import mediapipe as mp
import json
import os
import requests

# Caminho onde Frigate salva snapshots
SNAPSHOT_DIR = "/mnt/frigate/snapshots/"
HISTORY_FILE = "/app/history.json"

# Inicializa MediaPipe Pose
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(static_image_mode=True)

def analyze_image(image_path):
    img = cv2.imread(image_path)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = pose.process(img_rgb)
    
    status = "desconhecido"
    if results.pose_landmarks:
        # Exemplo simplificado de classificação
        y_coords = [lm.y for lm in results.pose_landmarks.landmark]
        torso_angle = max(y_coords) - min(y_coords)
        if torso_angle < 0.3:
            status = "caído"
        elif torso_angle < 0.6:
            status = "sentado"
        else:
            status = "em pé"
    return status

def main():
    status_report = {}
    for img_file in os.listdir(SNAPSHOT_DIR):
        if img_file.endswith(".jpg"):
            camera_name = img_file.split("_")[0]
            status_report[camera_name] = analyze_image(os.path.join(SNAPSHOT_DIR, img_file))
    
    # Salva histórico para comparação
    with open(HISTORY_FILE, "w") as f:
        json.dump(status_report, f)
    
    # Enviar para container de notificações
    requests.post("http://notificacoes:5001/status", json=status_report)

if __name__ == "__main__":
    main()
```

* Roda a cada 5 minutos via cron ou scheduler do Docker:

```bash
*/5 * * * * docker exec openpose_container python /app/analyze.py
```

---

### **2.3 Container 3: Notificações**

**Dockerfile básico**:

```dockerfile
FROM python:3.11-slim
RUN pip install flask requests python-telegram-bot
WORKDIR /app
COPY notify.py /app/notify.py
CMD ["python", "notify.py"]
```

**`notify.py`** – exemplo usando Flask + Telegram:

```python
from flask import Flask, request
import telegram

app = Flask(__name__)

BOT_TOKEN = "SEU_BOT_TOKEN"
CHAT_ID = "SEU_CHAT_ID"
bot = telegram.Bot(token=BOT_TOKEN)

@app.route("/status", methods=["POST"])
def status():
    data = request.json
    message = ""
    for camera, status in data.items():
        message += f"{camera}: {status}\n"
        if status == "caído":
            message = f"ALERTA! {camera} detectado caído!\n" + message
    bot.send_message(chat_id=CHAT_ID, text=message)
    return {"ok": True}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
```

* Recebe o JSON do container OpenPose e envia mensagem via Telegram.

---

## **3️⃣ Cronograma de Implantação**

1. Configurar Raspberry Pi Zero 2W com Tailscale e subnet routing.
2. Testar acesso remoto às câmeras pelo Proxmox via Tailscale.
3. Configurar Docker containers no Proxmox:

   * Frigate → capturar e armazenar snapshots
   * OpenPose → processar snapshots
   * Notificações → enviar Telegram / alertas
4. Testar pipeline completo:

   * Snapshots → análise → JSON → notificações
5. Ajustar thresholds de postura, intervalos e mensagens de alerta.
