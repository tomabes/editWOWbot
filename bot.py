import os
import logging
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from dotenv import load_dotenv
import json

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PUTER_API_KEY = os.getenv("PUTER_API_KEY")

logging.basicConfig(level=logging.INFO)

user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Пришли текст поста первым сообщением, а потом изображения с правками. Когда будешь готов — отправь команду /generate для запуска обработки.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id] = {'post': update.message.text, 'images': []}
    await update.message.reply_text("Текст поста сохранён. Жду скрины с правками.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data:
        await update.message.reply_text("Сначала пришли текст поста.")
        return

    photo = update.message.photo[-1]
    file = await photo.get_file()
    file_path = f"temp_{user_id}_{len(user_data[user_id]['images'])}.jpg"
    await file.download_to_drive(file_path)

    user_data[user_id]['images'].append(file_path)
    await update.message.reply_text("Картинка сохранена.")

async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data:
        await update.message.reply_text("Нет текста и скриншотов.")
        return

    post = user_data[user_id]['post']
    images = user_data[user_id]['images']

    files = [("files", (os.path.basename(p), open(p, "rb"))) for p in images]

    headers = {
        "Authorization": f"Bearer {PUTER_API_KEY}",
    }

    multipart_data = {
        "model": "claude-3-sonnet",
        "messages": [
            {
                "role": "system",
                "content": "Ты — редактор. Пользователь присылает текст поста и скрины с правками. Исправь текст в соответствии с изображениями. Отправь только исправленный текст."
            },
            {
                "role": "user",
                "content": f"Вот текст поста:\n\n{post}\n\nПравки на изображениях."
            }
        ]
    }

    response = requests.post(
        "https://api.puter.com/chat/completions",
        headers={"Authorization": f"Bearer {PUTER_API_KEY}"},
        files=files + [('payload', (None, json.dumps(multipart_data), 'application/json'))]
    )

    for path in images:
        os.remove(path)

    user_data.pop(user_id)

    if response.status_code == 200:
        result = response.json()
        reply = result['choices'][0]['message']['content']
        await update.message.reply_text(reply)
    else:
        await update.message.reply_text("Ошибка при обращении к Claude. Проверь API ключ или формат запроса.")

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("generate", generate))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.run_polling()

if __name__ == "__main__":
    main()
