import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

BOT_TOKEN = "8885379423:AAGbn9nfZj-I4_nzC0mU9Aec0y23GGbzaLY"
ADMIN_ID = 5206473963
CHAT_ID = -1003978554378

async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Получено сообщение из чата с ID: {update.effective_chat.id}")
    if update.effective_chat.id == CHAT_ID:
        print("Сообщение из нужной группы, пересылаю...")
        try:
            await context.bot.forward_message(
                chat_id=ADMIN_ID,
                from_chat_id=update.effective_chat.id,
                message_id=update.effective_message.message_id
            )
            print("Переслано успешно!")
        except Exception as e:
            print(f"Ошибка при пересылке: {e}")
    else:
        print(f"ID чата не совпадает: {update.effective_chat.id} != {CHAT_ID}")

def main():
    # Увеличиваем таймауты до 120 секунд
    app = Application.builder() \
        .token(BOT_TOKEN) \
        .connect_timeout(120) \
        .read_timeout(120) \
        .build()
    app.add_handler(MessageHandler(~filters.COMMAND, forward_message))
    print("Бот запущен и слушает сообщения...")
    print(f"Ожидаемый CHAT_ID: {CHAT_ID}")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
