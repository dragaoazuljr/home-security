from flask import Flask, Response, render_template_string
import cv2
import threading

app = Flask(__name__)

import os
# Cameras URLs from environment variable CAMERAS, separated by ';'
CAMERAS = [url for url in os.getenv('CAMERAS', '').split(';') if url]


# Store VideoCapture objects per camera index
caps = {}
lock = threading.Lock()

def get_capture(idx):
    with lock:
        if idx not in caps:
            # Use FFMPEG backend and force TCP transport for better compatibility
            caps[idx] = cv2.VideoCapture(CAMERAS[idx], cv2.CAP_FFMPEG)
        return caps[idx]

def generate_frames(idx):
    cap = get_capture(idx)
    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        # Encode as JPEG
        _, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def index():
    # Simple HTML page with a grid of <img> tags pointing to streams
    html = """
<!doctype html>
<html lang=\"en\">
<head><meta charset=\"UTF-8\"><title>Câmeras</title></head>
<body style='margin:0;display:flex;flex-wrap:wrap;'>
{% for i in range(cameras|length) %}
  <img src=\"/stream/{{i}}\" style='width:50%;height:auto'>
{% endfor %}
</body>
</html>
    """
    return render_template_string(html, cameras=CAMERAS)

@app.route('/stream/<int:cam_id>')
def stream(cam_id):
    if cam_id < 0 or cam_id >= len(CAMERAS):
        return "Invalid camera", 404
    return Response(generate_frames(cam_id), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
