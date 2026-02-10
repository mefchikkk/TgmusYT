import logging
import os
import asyncio
import socket
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

# --- КОНФИГУРАЦИЯ ---
TOKEN = "8329570198:AAF1qLINA-u2Blhzi2dpg3_xSzRdqUybeaM"
TEMP_DIR = Path("temp_audio")
TEMP_DIR.mkdir(exist_ok=True)

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- ХАК ДЛЯ СЕТИ (Forcing IPv4) ---
# Это заставит бота игнорировать IPv6, который часто глючит в Docker
orig_getaddrinfo = socket.getaddrinfo

def getaddrinfo_ipv4(host, port, family=0, type=0, proto=0, flags=0):
    return orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)

socket.getaddrinfo = getaddrinfo_ipv4
# -----------------------------------

# Настройки yt-dlp для слабых серверов (50MB RAM)
YDL_OPTS = {
    # 'worst' - самое низкое качество, чтобы файл весил мало и не забивал память
    # Мы не используем merge (склейку), чтобы не запускать тяжелый FFmpeg
    'format': 'worst[ext=mp4]/best', 
    'outtmpl': str(TEMP_DIR / '%(id)s.%(ext)s'),
    'noplaylist': True,
    'quiet': False,        # Вывод логов в консоль
    'verbose': True,       # Подробные ошибки
    'nocheckcertificate': True,
    'source_address': '0.0.0.0', # Еще одна попытка заставить работать сеть
    'socket_timeout': 15,
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я готов.\n"
        "Я работаю в режиме ЭКОНОМИИ (50 МБ RAM).\n"
        "Отправь мне ссылку на YouTube, и я скачаю видео в низком качестве (чтобы не упасть)."
    )

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    
    # Фильтр: работаем только с ссылками
    if not (url.startswith("http://") or url.startswith("https://")):
        await update.message.reply_text("⚠️ Это не ссылка. Отправь ссылку на YouTube.")
        return

    status_msg = await update.message.reply_text("🔎 Проверяю ссылку и память... ⏳")
    print(f"DEBUG: Начало обработки {url}")

    file_path = None

    try:
        # 1. Скачивание
        def run_download():
            print("DEBUG: Запускаю yt-dlp...")
            with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info)

        loop = asyncio.get_running_loop()
        # Запускаем в отдельном потоке, чтобы бот не завис
        file_path = await loop.run_in_executor(None, run_download)
        
        print(f"DEBUG: Файл скачан: {file_path}")

        # 2. Проверка файла
        if not file_path or not os.path.exists(file_path):
            await status_msg.edit_text("❌ Ошибка: Файл не найден после скачивания.")
            return

        file_size = os.path.getsize(file_path) / (1024 * 1024)
        print(f"DEBUG: Размер файла: {file_size:.2f} MB")

        if file_size > 49:
            await status_msg.edit_text(f"❌ Файл слишком большой ({file_size:.1f} МБ). Лимит сервера — 50 МБ.")
            os.remove(file_path)
            return

        # 3. Отправка
        await status_msg.edit_text("🚀 Отправляю видео...")
        with open(file_path, 'rb') as video_file:
            await update.message.reply_video(
                video=video_file, 
                caption="✅ Скачано ботом (Low Quality Mode)",
                supports_streaming=True
            )
        
        print("DEBUG: Видео успешно отправлено")

    except Exception as e:
        error_text = str(e)
        print(f"CRITICAL ERROR: {error_text}")
        
        if "Network is unreachable" in error_text:
            await status_msg.edit_text("🚫 ОШИБКА СЕТИ: Хостинг блокирует доступ к YouTube.")
        elif "Killed" in error_text: # Это мы увидим только в консоли
            await status_msg.edit_text("☠️ ОШИБКА ПАМЯТИ: Бот был убит системой (Out of Memory).")
        else:
            await status_msg.edit_text(f"❌ Ошибка при скачивании:\n{error_text[:100]}")

    finally:
        # 4. Очистка
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"DEBUG: Файл {file_path} удален")
            except Exception as e:
                print(f"ERROR cleaning up: {e}")

def main():
    # --- ДИАГНОСТИКА СЕТИ ПРИ ЗАПУСКЕ ---
    print("--- ЗАПУСК БОТА ---")
    print("1. Проверка доступа к Google (DNS)...")
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=5)
        print("✅ Google DNS доступен.")
    except OSError as e:
        print(f"❌ Google DNS НЕДОСТУПЕН: {e}")

    print("2. Проверка доступа к YouTube...")
    try:
        socket.create_connection(("www.youtube.com", 80), timeout=5)
        print("✅ YouTube (порт 80) доступен.")
    except OSError as e:
        print(f"❌ YouTube НЕДОСТУПЕН: {e}")
        print("!!! ВНИМАНИЕ: Если YouTube недоступен, бот НЕ БУДЕТ качать видео !!!")
    # ------------------------------------

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))

    print("Бот переходит в режим ожидания сообщений...")
    app.run_polling()

if __name__ == "__main__":
    main()

