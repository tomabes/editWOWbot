import os
import logging
import base64
import openai
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY
logging.basicConfig(level=logging.INFO)

user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Пришли текст поста первым сообщением, а потом изображения с правками. Когда будешь готова — отправь команду /generate для запуска обработки.")

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
        await update.message.reply_text("Нет текста и скринов.")
        return

    post = user_data[user_id]['post']
    images = user_data[user_id]['images']

   content = [
    {
        "type": "text",
        "text": f"""Ты — редактор. Твоя задача — переписать предложенный текст так, чтобы он звучал живо, понятно и вовлекал читателя. Изображения содержат пометки с замечаниями и правками. Используй их как подсказки. Не пиши ничего лишнего — просто верни исправленный пост.

Вот текст поста:

{post}
"""
    }
]

    for path in images:
        with open(path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode("utf-8")
            image_data = {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"
                }
            }
            content.append(image_data)
        os.remove(path)

    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": content
                }
            ],
            max_tokens=1500
        )
        reply = response.choices[0].message.content
        await update.message.reply_text(reply)
    except Exception as e:
        await update.message.reply_text(f"Ошибка при обращении к OpenAI API:\n{e}")

    user_data.pop(user_id)

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("generate", generate))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.run_polling()

if __name__ == "__main__":
    main()
