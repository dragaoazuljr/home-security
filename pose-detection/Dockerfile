FROM python:3.11-slim

# Instala dependências necessárias para OpenCV e MediaPipe
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Instala bibliotecas Python
RUN pip install --no-cache-dir opencv-python numpy mediapipe requests

WORKDIR /app
COPY analyze.py /app/analyze.py
COPY analyze_ollama.py /app/analyze_ollama.py

#CMD ["python", "analyze.py"]
CMD ["python", "analyze_ollama.py"]
