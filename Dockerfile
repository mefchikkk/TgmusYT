# Используем официальный образ Python
FROM python:3.10-slim

# Устанавливаем ffmpeg и необходимые системные библиотеки
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Создаем рабочую директорию
WORKDIR /app

# Копируем файл зависимостей и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все остальные файлы бота в контейнер
COPY . .

# Команда для запуска бота
CMD ["python", "bottg.py"]
