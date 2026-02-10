FROM python:3.10-slim

# Установка FFmpeg
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Установка библиотек
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY . .

# Запуск с ключом -u для моментальных логов
CMD ["python", "-u", "bottg.py"]
