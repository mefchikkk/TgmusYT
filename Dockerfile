FROM python:3.10-slim

# Устанавливаем только самое необходимое
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Запуск напрямую через python
CMD ["python", "bottg.py"]
