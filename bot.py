import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# --- ВАШИ ДАННЫЕ ---
BOT_TOKEN = "8885379423:AAGbn9nfZj-I4_nzC0mU9Aec0y23GGbzaLY"
ADMIN_ID = 5206473963
CHAT_ID = -1003978554378
# -------------------

# Health-сервер для Render (порт 10000)
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args):
        pass  # Отключаем лишние логи

def run_health_server():
    server = HTTPServer(('0.0.0.0', 10000), HealthHandler)
    server.serve_forever()

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
    # Запускаем Health-сервер в фоновом потоке
    thread = threading.Thread(target=run_health_server, daemon=True)
    thread.start()

    # Бот с увеличенными таймаутами и автоматическими переподключениями
    app = Application.builder() \
        .token(BOT_TOKEN) \
        .connect_timeout(300) \
        .read_timeout(300) \
        .build()

    app.add_handler(MessageHandler(~filters.COMMAND, forward_message))

    print("Бот запущен и слушает сообщения...")
    print(f"Ожидаемый CHAT_ID: {CHAT_ID}")

    # Бесконечный цикл переподключения при ошибках
    while True:
        try:
            app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
        except Exception as e:
            print(f"Ошибка: {e}. Переподключение через 10 секунд...")
            time.sleep(10)
            continue
        break

if __name__ == "__main__":
    main()
