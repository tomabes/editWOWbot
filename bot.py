import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from dotenv import load_dotenv
from together import Together

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")

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

    image_texts = [f"Скриншот: {os.path.basename(path)} — правки на этом изображении." for path in images]

    for path in images:
        os.remove(path)

    full_prompt = f"""Ты — редактор. Пользователь присылает текст поста и скрины с правками.
Вот текст поста:

{post}

Вот правки, сделанные пользователем на изображениях:
{chr(10).join(image_texts)}

Отредактируй текст поста, учтя замечания. Верни только исправленный текст.
"""

    client = Together(api_key=TOGETHER_API_KEY)

    try:
        response = client.chat.completions.create(
            model="meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
            messages=[{"role": "user", "content": full_prompt}]
        )
        reply = response.choices[0].message.content
        await update.message.reply_text(reply)
    except Exception as e:
        await update.message.reply_text(f"Ошибка при обращении к Together API:\n{e}")

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
