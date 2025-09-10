import cv2
import mediapipe as mp
import json
import os
import requests

# Diretórios configuráveis via env
SNAPSHOT_DIR = os.environ.get("SNAPSHOT_DIR", "/app/snapshots/")
HISTORY_FILE = os.environ.get("HISTORY_FILE", "/app/history.json")

# Extensões aceitas
VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

# Inicializa MediaPipe Pose
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(static_image_mode=True)

def analyze_image(image_path):
    img = cv2.imread(image_path)
    if img is None:
        return "erro_leitura"
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = pose.process(img_rgb)

    print(f"Análisando imagem: {image_path}")
    print(f"Resultados da análise: {results.pose_landmarks}")
    
    status = "desconhecido"
    if results.pose_landmarks:
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
        _, ext = os.path.splitext(img_file.lower())
        if ext not in VALID_EXTENSIONS:
            continue
        camera_name = os.path.splitext(img_file)[0]
        img_path = os.path.join(SNAPSHOT_DIR, img_file)
        status_report[camera_name] = analyze_image(img_path)
    
    # Salva histórico
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(status_report, f, indent=2)
    
    # Enviar para container de notificações (se disponível)
    try:
        # requests.post("http://notificacoes:5001/status", json=status_report, timeout=5)
        print("Status enviado para notificações:", status_report)  # Substituído por um print para fins de teste.
    except Exception as e:
        print("Erro ao enviar notificações:", e)

if __name__ == "__main__":
    main()
