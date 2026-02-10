FROM python:3.10-slim

# 1. Настройка вывода логов (чтобы видеть ошибки сразу)
ENV PYTHONUNBUFFERED=1

# 2. Установка системных программ (FFmpeg нужен для хорошего качества видео)
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# 3. Рабочая папка
WORKDIR /app

# 4. Установка библиотек Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Копирование кода бота
COPY . .

# 6. Запуск бота
CMD ["python", "bottg.py"]
