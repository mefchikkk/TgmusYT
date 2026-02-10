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
    'format': 'worst[ext=mp4]/best', # Качаем самый маленький файл, чтобы не вылететь по памяти
    'outtmpl': str(TEMP_DIR / '%(title)s.%(ext)s'),
    'noplaylist': True,
    'quiet': False, # Видим логи в консоли!
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

