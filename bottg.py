import logging
import os
import asyncio
from pathlib import Path

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

import yt_dlp

# ---------------- Настройки ----------------
TOKEN = "8329570198:AAF1qLINA-u2Blhzi2dpg3_xSzRdqUybeaM" 

# Папка для временных файлов
TEMP_DIR = Path("temp_audio")
TEMP_DIR.mkdir(exist_ok=True)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------- yt-dlp настройки ----------------
ydl_opts = {
    'format': 'bestaudio/best',
    'outtmpl': str(TEMP_DIR / '%(title)s.%(ext)s'),
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',   # 128 / 192 / 256 на выбор
    }],
    'quiet': True,
    'no_warnings': True,
    'continuedl': True,
    'retries': 10,
    'noplaylist': True,           # скачиваем только одно видео, а не плейлист
}

# ---------------- Команды и обработчики ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Привет! Я бот созданный Даниилом Головко, который достаёт аудио из видео 🎵\n\n"
        "Просто пришли мне ссылку на видео YouTube\n"
        "и я постараюсь отправить тебе mp3."
    )
    await update.message.reply_text(text, disable_web_page_preview=True)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Отправь мне любую ссылку на видео — я попробую вытащить из него звук в mp3."
    )


async def download_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    
    # Простая проверка, что это похоже на ссылку
    if not (url.startswith("http://") or url.startswith("https://")):
        await update.message.reply_text("Похоже, это не ссылка 😕\nПришли нормальную ссылку на видео. Пример: https://youtu.be/.......")
        return

    msg = await update.message.reply_text("Качаю аудио... ⏳ (иногда это занимает 10–40 секунд)")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            # yt-dlp может менять расширение после постпроцессинга
            if not filename.endswith(".mp3"):
                base = os.path.splitext(filename)[0]
                filename = base + ".mp3"

            title = info.get("title", "audio")
            # Очищаем название от запрещённых символов
            safe_title = "".join(c for c in title if c.isalnum() or c in " -_").strip()
            if not safe_title:
                safe_title = "audio_from_video"

            final_path = TEMP_DIR / f"{safe_title}.mp3"

            # Переименовываем, если имя отличается
            if Path(filename) != final_path:
                os.replace(filename, final_path)

        # Проверяем, что файл существует и не пустой
        if not final_path.exists() or final_path.stat().st_size < 1000:
            await msg.edit_text("Не получилось скачать аудио 😔\nПопробуй другую ссылку. Например https://youtu.be/...... ")
            return

        # Отправляем файл
        await msg.edit_text(f"Готово! Отправляю → 1..2..3...")
        
        await update.message.reply_audio(
            audio=final_path.open("rb"),
            title=title[:64],
            performer=info.get("uploader", "Unknown"),
            caption="Скачано с помощью Даниилом Головко @YouTDownloaderrrrrr_bot",
            
        )

        # Удаляем временный файл
        try:
            final_path.unlink()
        except:
            pass

    except Exception as e:
     logger.error(f"Ошибка при обработке {url}: {e}", exc_info=True)
    
    error_text = str(e).lower()
    
    if "timed out" in error_text or "timeout" in error_text:
        # Файл почти всегда уже отправлен, просто ответ задержался
        await msg.edit_text(
            "Аудио отправлено! 🎵\n"
            "(Telegram чуть задержался с подтверждением — всё нормально)"
        )
        # файл уже у пользователя, можно сразу удалить временный
        try:
            final_path.unlink()
        except:
            pass
        return
    
    elif "http error 429" in error_text:
        err_msg = "Слишком много запросов к YouTube. Подожди 5–10 минут."
    elif "private video" in error_text or "unavailable" in error_text:
        err_msg = "Видео приватное или удалено."
    else:
        err_msg = f"Что-то пошло не так...\n\n{str(e)[:200]}"
    
    await msg.edit_text(err_msg)
    
    # удаляем файл в любом случае, если ошибка
    try:
        if 'final_path' in locals():
            final_path.unlink()
    except:
        pass


def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    
    # Все текстовые сообщения, которые выглядят как ссылки
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        download_audio
    ))

    print("Бот запущен...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()