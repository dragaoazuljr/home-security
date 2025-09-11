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

## **2️⃣ Proxmox – Container Único**

Agora todo o sistema roda em **um único container** que contém:

* Captura de snapshots das câmeras (via Frigate ou RTSP simples).
* Analisador de postura (MediaPipe / OpenPose).
* Geração de relatório global (comparando histórico).
* Envio das análises e relatórios para o Telegram.

O container terá:

* Dockerfile que instala dependências (opencv, mediapipe, requests, python-telegram-bot, flask, etc.).
* Scripts Python:

  * `analyze.py` → processa snapshots e classifica posturas.
  * `report.py` → gera relatórios globais comparando histórico.
  * `notify.py` → envia mensagens e imagens para o Telegram.

### **2.1 Volumes**

* `/mnt/frigate/snapshots` → snapshots das câmeras.
* `/app/history.json` → histórico de análises.
* `/app/results.json` → último relatório consolidado.

### **2.2 Variáveis de Ambiente**

Configurar no `docker run` ou `docker-compose`:

* `BOT_TOKEN` → Token do bot do Telegram (BotFather).
* `CHAT_ID` → Chat ID do grupo ou usuário.
* `SNAPSHOT_DIR` → Caminho para snapshots (default: `/mnt/frigate/snapshots/`).
* `OUTPUT_FILE` → Onde salvar os relatórios (default: `/app/results.json`).

---

## **3️⃣ Pipeline de Execução**

1. **Captura de imagens**
   O Frigate ou outra fonte RTSP salva snapshots em `/mnt/frigate/snapshots`.

2. **Análise automática**
   O script analisa cada snapshot, classifica posturas (`em pé`, `sentado`, `caído`) e salva em `history.json`.

3. **Geração de relatório global**
   O sistema compara o relatório atual com o anterior e define o **nível geral de risco da casa** (🟢, 🟠, 🔴).

4. **Notificações no Telegram**

   * Envia o relatório consolidado em texto.
   * Anexa as imagens relacionadas.
   * Alerta imediato se detectar risco **🔴**.

---

## **4️⃣ Cronograma de Implantação**

1. Configurar Raspberry Pi Zero 2W com Tailscale e subnet routing.
2. Testar acesso remoto às câmeras pelo Proxmox via Tailscale.
3. Criar o container único no Proxmox com todos os scripts.
4. Configurar variáveis de ambiente (`BOT_TOKEN`, `CHAT_ID`, etc.).
5. Testar pipeline completo:

   * Snapshots → análise → relatório → alerta Telegram.
6. Ajustar thresholds, intervalos e mensagens de alerta conforme necessário.
