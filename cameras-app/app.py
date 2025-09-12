import os
import subprocess
import cv2
import numpy as np
from flask import Flask, Response, render_template_string

app = Flask(__name__)

# --- LÊ AS CÂMERAS DO ENV ---
# Formato: "url,width,height;url2,width2,height2"
CAMERAS = []
raw_env = os.getenv("CAMERAS", "")
if raw_env:
    for entry in raw_env.split(";"):
        parts = entry.strip().split(",")
        if len(parts) == 3:
            try:
                CAMERAS.append({
                    "url": parts[0],
                    "width": int(parts[1]),
                    "height": int(parts[2])
                })
            except ValueError:
                print(f"⚠️ Ignorando entrada inválida (width/height não é número): {entry}")
        else:
            print(f"⚠️ Ignorando entrada inválida (formato url,width,height): {entry}")


def generate_frames(url, width, height):
    """Captura frames via ffmpeg e gera stream MJPEG."""
    command = [
        "ffmpeg",
        "-rtsp_transport", "udp",  # funciona na sua câmera
        "-i", url,
        "-an", # descarta áudio
        "-vf", f"scale={width}:{height}",  # força a resolução
        "-r", "10",
        "-f", "image2pipe",
        "-pix_fmt", "bgr24",
        "-vcodec", "rawvideo",
        "-"
    ]

    proc = subprocess.Popen(command, stdout=subprocess.PIPE, bufsize=10**8)

    while True:
        frame_size = width * height * 3
        raw_frame = proc.stdout.read(frame_size)
        if len(raw_frame) != frame_size:
            continue  # ou reconecta

        frame = np.frombuffer(raw_frame, np.uint8).reshape((height, width, 3))
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')


@app.route('/')
def index():
    """Página principal com grid das câmeras."""
    html = """
<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Camera Streams</title>
<style>
body { margin:0; background:#121212; font-family:sans-serif; }
.container { display:grid; grid-template-columns: repeat(auto-fit,minmax(400px,1fr)); gap:5px; }
.stream-wrapper { position:relative; background:#000; }
.stream-wrapper img { width:100%; display:block; }
.label { position:absolute; top:10px; left:10px; background:rgba(0,0,0,0.6); padding:5px 10px; border-radius:5px; color:white; }
</style>
</head>
<body>
<div class="container">
{% for i in range(cameras_count) %}
  <div class="stream-wrapper">
    <img src="/stream/{{i}}">
    <div class="label">Camera {{i+1}}</div>
  </div>
{% endfor %}
</div>
</body>
</html>
"""
    return render_template_string(html, cameras_count=len(CAMERAS))


@app.route('/stream/<int:cam_id>')
def stream(cam_id):
    if cam_id < 0 or cam_id >= len(CAMERAS):
        return "Câmera inválida", 404
    cam = CAMERAS[cam_id]
    print(f"🎥 Iniciando stream da câmera {cam_id}: {cam['url']} ({cam['width']}x{cam['height']})")
    return Response(generate_frames(cam["url"], cam["width"], cam["height"]),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    if not CAMERAS:
        print("❌ Nenhuma câmera configurada. Use: export CAMERAS='rtsp://user:pass@ip:554/stream,1920,1080'")
    else:
        print(f"✅ {len(CAMERAS)} câmera(s) configurada(s). Iniciando servidor...")
        app.run(host='0.0.0.0', port=5000, threaded=True)
