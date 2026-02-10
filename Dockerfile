FROM python:3.10-slim

# Ставим FFmpeg и обновляем сертификаты (важно для YouTube!)
RUN apt-get update && \
    apt-get install -y ffmpeg ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Ставим зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY . .

# Создаем папку для загрузок
RUN mkdir -p temp_audio && chmod 777 temp_audio

# ЗАПУСК С КЛЮЧОМ -u (ОБЯЗАТЕЛЬНО!)
CMD ["python", "-u", "bottg.py"]
