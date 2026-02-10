import logging
import os
import asyncio
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import yt_dlp

# Настройки
TOKEN = "8329570198:AAF1qLINA-u2Blhzi2dpg3_xSzRdqUybeaM"
TEMP_DIR = Path("temp_audio")
TEMP_DIR.mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO)

# Ультра-легкие настройки для 50МБ памяти
YDL_OPTS = {
    'format': 'worst[ext=mp4]/best', # Самое легкое видео
    'outtmpl': str(TEMP_DIR / '%(title)s.%(ext)s'),
    'noplaylist': True,
    'quiet': False,
    'verbose': True,
    
    # --- НАБОР ДЛЯ ОБХОДА БЛОКИРОВОК ---
    'source_address': '0.0.0.0',       # Принудительно IPv4 (самое важное!)
    'nocheckcertificate': True,        # Игнорировать ошибки SSL
    'socket_timeout': 30,              # Дать серверу больше времени на ответ
    'retries': 5,                      # Пробовать 5 раз, если не вышло
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'web'],
            'skip': ['dash', 'hls']    # Пропускаем сложные протоколы
        }
    },
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
}
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_photo(
            photo=open("welcome.jpg", "rb"),
            caption="Привет! Пришли ссылку на YouTube, и я попробую скачать её (самое низкое качество для экономии памяти)."
        )
    except:
        await update.message.reply_text("Привет! Пришли ссылку на YouTube.")

async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("http"): return

    msg = await update.message.reply_text("Начинаю загрузку... ⏳")
    print(f"DEBUG: Старт загрузки {url}")

    try:
        def run_ydl():
            with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info)

        loop = asyncio.get_running_loop()
        # Самый опасный момент: если тут бот упадет — памяти слишком мало
        filename = await loop.run_in_executor(None, run_ydl)
        
        print(f"DEBUG: Файл скачан: {filename}")
        await msg.edit_text("Готово! Отправляю файл...")

        with open(filename, 'rb') as f:
            await update.message.reply_video(video=f)
        
        os.remove(filename) # Чистим за собой сразу

    except Exception as e:
        print(f"ERROR: {e}")
        await msg.edit_text(f"Ошибка: {e}")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download))
    print("Бот запущен и готов к работе!")
    app.run_polling()

if __name__ == "__main__":
    main()


