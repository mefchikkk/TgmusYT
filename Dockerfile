FROM python:3.10-slim

# Отключаем буферизацию логов
ENV PYTHONUNBUFFERED=1

# Устанавливаем ffmpeg и необходимые инструменты
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Проверяем, что ffmpeg установился (выведется в логи сборки)
RUN ffmpeg -version

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bottg.py"]
