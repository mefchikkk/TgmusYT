import logging
import asyncio
import os
import subprocess
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler,
)

import yt_dlp
from cleaner import cleanup_temp

# ---------------- Настройки ----------------
TOKEN = "8329570198:AAF1qLINA-u2Blhzi2dpg3_xSzRdqUybeaM"

TEMP_DIR = Path("temp_audio")
TEMP_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

ydl_opts = {
    'format': 'bestaudio/best',
    'outtmpl': str(TEMP_DIR / '%(title)s.%(ext)s'),
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'quiet': True,
    'writethumbnail': True,  # Скачивать обложку видео
    'no_warnings': True,
    'continuedl': True,
    'retries': 10,
    'noplaylist': True,
}

# ---------------- Команды ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Сбрасываем предыдущие данные
    context.user_data.pop("mode", None)
    context.user_data.pop("quality", None)

    keyboard = [
        [InlineKeyboardButton("🎵 Скачать аудио", callback_data="audio")],
        [InlineKeyboardButton("🎬 Скачать видео", callback_data="video")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = (
        "Привет! Я сервис Даниила Г. Мой сервис предоставляет данные опции: скачивать аудио или видео из YouTube 🎬🎵\n\n"
        "Выбери, что хочешь скачать:"
    )


    await update.message.reply_photo(
    photo=open("welcome.jpg", "rb"),  # твоя картинка
    caption=text,                     # текст под фото
    reply_markup=reply_markup         # ОБЯЗАТЕЛЬНО передаем кнопки сюда
)



async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Выбери формат и отправь ссылку на YouTube. Для видео обязательно выбери качество."
    )

# ---------------- Callback кнопки ----------------

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "audio":
        context.user_data["mode"] = "audio"
        context.user_data.pop("quality", None)
        
        # ИСПРАВЛЕНИЕ: используем edit_message_caption, так как исходное сообщение - это ФОТО
        await query.edit_message_caption(
            caption="🎵 Режим выбран: АУДИО\nОтправь ссылку на YouTube.",
            reply_markup=None # Убираем кнопки или ставим новые, если нужно
        )

    elif data == "video":
        context.user_data["mode"] = "video"
        context.user_data.pop("quality", None)
        
        keyboard = [
            [
                InlineKeyboardButton("🎬 360p", callback_data="360"),
                InlineKeyboardButton("🎬 720p", callback_data="720"),
                InlineKeyboardButton("🎬 1080p", callback_data="1080"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # ИСПРАВЛЕНИЕ: используем edit_message_caption
        await query.edit_message_caption(
            caption="🎬 Режим выбран: ВИДЕО\nВыбери качество видео:", 
            reply_markup=reply_markup
        )

    elif data in ["360", "720", "1080"]:
        context.user_data["quality"] = data
        
        # ИСПРАВЛЕНИЕ: используем edit_message_caption
        await query.edit_message_caption(
            caption=f"🎬 Выбрано качество видео: {data}p\nТеперь отправь ссылку на YouTube.",
            reply_markup=None
        )

# ---------------- Скачивание ----------------

async def download_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    mode = context.user_data.get("mode", None)

    if not (url.startswith("http://") or url.startswith("https://")):
        await update.message.reply_text("Это не ссылка 😕\nПришли нормальную ссылку на YouTube.")
        return

    # Проверка обязательного выбора качества для видео
    if mode == "video" and "quality" not in context.user_data:
        await update.message.reply_text("⚠️ Сначала выбери качество видео!")
        return
    elif mode is None:
        await update.message.reply_text("⚠️ Сначала выбери режим: аудио или видео!")
        return 
    quality = context.user_data.get("quality", None)
    msg = await update.message.reply_text("Обрабатываю... ⏳")
    final_path = None
    compressed_path = None

    try:
        opts = ydl_opts.copy()
        if mode == "video":
            format_str = "bestvideo+bestaudio/best"
            if quality:
                format_str = f"bestvideo[height<={quality}]+bestaudio/best"
            opts = {
                'format': format_str,
                'outtmpl': str(TEMP_DIR / '%(title)s.%(ext)s'),
                'merge_output_format': 'mp4',
                'quiet': True,
                'no_warnings': True,
                'continuedl': True,
                'retries': 10,
                'noplaylist': True,
            }

        # Эта внутренняя функция делает «грязную» работу по скачиванию
        def run_ydl(url, options):
            with yt_dlp.YoutubeDL(options) as ydl:
                info_dict = ydl.extract_info(url, download=True)
                return info_dict, ydl.prepare_filename(info_dict)

        # А эта строка говорит боту: "Скачивай, но не замирай, дай другим юзерам тоже писать"
        loop = asyncio.get_running_loop()
        info, filename = await loop.run_in_executor(None, run_ydl, url, opts)
        
        # Дальше идет твой прежний код обработки названия
        title = info.get("title", "media")
        title = info.get("title", "media")
        safe_title = "".join(c for c in title if c.isalnum() or c in " -_").strip()
        if not safe_title:
                safe_title = "media_from_video"

        if mode == "audio":
                if not filename.endswith(".mp3"):
                    filename = os.path.splitext(filename)[0] + ".mp3"
                final_path = TEMP_DIR / f"{safe_title}.mp3"
        else:
                final_path = TEMP_DIR / f"{safe_title}.mp4"

        if Path(filename) != final_path:
                os.replace(filename, final_path)

        if not final_path.exists() or final_path.stat().st_size < 1000:
            await msg.edit_text("Не получилось скачать 😔 Попробуй другую ссылку.")
            return

        if mode == "audio":
            file_size_mb = final_path.stat().st_size / (1024 * 1024)
            if file_size_mb > 48:
                await msg.edit_text("Файл большой — сжимаю... ⏳")
                compressed_path = TEMP_DIR / f"{safe_title}_compressed.mp3"
                subprocess.run([
                    'ffmpeg', '-i', str(final_path),
                    '-b:a', '128k',
                    str(compressed_path)
                ], check=True, capture_output=True)
                final_path.unlink()
                final_path = compressed_path
                compressed_path = None

        await msg.edit_text("🎬 Почти у цели! Отправляю...")

        thumb_path = Path(filename).with_suffix(".webp")
        if not thumb_path.exists():
            thumb_path = Path(filename).with_suffix(".jpg")

        if mode == "audio":
            await update.message.reply_audio(
                audio=final_path.open("rb"),
                thumbnail=thumb_path.open("rb") if thumb_path.exists() else None, # ВОТ ЭТА СТРОКА
                title=title[:64],
                performer=info.get("uploader", "Unknown"),
                caption=f"Скачано с помощью сервиса Даниила Г. @YouTDownloaderrrrrr_bot\nСпасибо за использование! 🎬🎵",
            )
        else:
            await update.message.reply_video(
                video=final_path.open("rb"),
                caption=f"Скачано с помощью сервиса Даниила Г. @YouTDownloaderrrrrr_bot\nКачество: {quality}🎬\nСпасибо за использование! 🎬🎵",
            )

    except Exception as e:
        logger.error(f"Ошибка при обработке {url}: {e}", exc_info=True)

    finally:
        cleanup_temp()

# ---------------- main ----------------

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        download_media
    ))

    print("Бот запущен...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
