import asyncio
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler, CallbackQueryHandler

# ---------- КОНФИГУРАЦИЯ ----------
BOT_TOKEN = "8885379423:AAGbn9nfZj-I4_nzC0mU9Aec0y23GGbzaLY"
ADMIN_ID = 5206473963
CHAT_ID = -1003978554378
# ---------------------------------

# База знаний (FAQ)
FAQ = {
    "светотень": "Светотени на стенах возникают из-за неравномерного нанесения краски или плохой подготовки. Обычно помогает перекраска с валиком с длинным ворсом.",
    "штукатурка": "Штукатурка должна сохнуть минимум 7 дней перед покраской.",
    "потолок": "Для потолка лучше использовать матовую краску – она скрывает неровности.",
    "плитка": "Для ванной используйте влагостойкий клей и затирку с антигрибковыми добавками.",
    "цена": "Цены зависят от объёма и состояния поверхностей. Напишите мне в личные сообщения.",
    "сроки": "Обычно отделка квартиры 50 м² занимает 2–3 недели.",
}

# ---------- МЕНЮ ----------
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("💰 Стоимость и услуги", callback_data="prices")],
        [InlineKeyboardButton("📝 Записаться на замер", callback_data="order")],
        [InlineKeyboardButton("❓ Готовые ответы", callback_data="faq")],
        [InlineKeyboardButton("📸 Показать проблему на фото", callback_data="report")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_menu():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Вернуться в меню", callback_data="back")]])

# ---------- HEALTH-СЕРВЕР ----------
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args):
        pass

def run_health_server():
    server = HTTPServer(('0.0.0.0', 10000), HealthHandler)
    server.serve_forever()

# ---------- ОСНОВНЫЕ ОБРАБОТЧИКИ ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я бот-помощник по отделке.\n"
        "Выберите, что вам нужно:",
        reply_markup=get_main_menu()
    )

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📋 Главное меню:", reply_markup=get_main_menu())

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "prices":
        text = (
            "💰 **Наши услуги:**\n\n"
            "• Покраска стен – от 500 ₽/м²\n"
            "• Штукатурка – от 800 ₽/м²\n"
            "• Натяжные потолки – от 700 ₽/м²\n"
            "• Укладка плитки – от 1500 ₽/м²\n"
            "• Устранение косяков – от 2000 ₽ за стену\n\n"
            "Точную стоимость рассчитаем после замера."
        )
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=get_back_menu())

    elif data == "order":
        await query.edit_message_text(
            "📝 Скоро здесь появится форма для записи на замер. А пока напишите мне в личные сообщения.",
            reply_markup=get_back_menu()
        )

    elif data == "faq":
        text = "❓ **Готовые ответы:**\n\n"
        for keyword, answer in FAQ.items():
            text += f"• *{keyword.capitalize()}* — {answer}\n\n"
        text += "Если не нашли ответ, просто напишите свой вопрос."
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=get_back_menu())

    elif data == "report":
        await query.edit_message_text(
            "📸 Скоро здесь появится возможность отправить фото проблемы. А пока напишите мне в личные сообщения.",
            reply_markup=get_back_menu()
        )

    elif data == "back":
        await query.edit_message_text("Главное меню:", reply_markup=get_main_menu())

# ---------- ПЕРЕСЫЛКА ИЗ ГРУППЫ ----------
async def forward_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == CHAT_ID:
        if update.message and update.message.text and update.message.text.startswith('/'):
            return
        try:
            await context.bot.forward_message(
                chat_id=ADMIN_ID,
                from_chat_id=update.effective_chat.id,
                message_id=update.effective_message.message_id
            )
            print("Сообщение переслано")
        except Exception as e:
            print(f"Ошибка пересылки: {e}")

async def auto_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Если сообщение из личного чата с ботом и содержит ключевое слово – отвечаем
    if update.effective_chat.type == "private":
        text = update.message.text
        if text:
            text_lower = text.lower()
            for keyword, answer in FAQ.items():
                if keyword in text_lower:
                    await update.message.reply_text(answer)
                    return
    # Иначе пересылаем админу, если сообщение из группы
    if update.effective_chat.id == CHAT_ID:
        await forward_to_admin(update, context)

# ---------- ГЛАВНАЯ ФУНКЦИЯ ----------
def main():
    thread = threading.Thread(target=run_health_server, daemon=True)
    thread.start()

    app = Application.builder().token(BOT_TOKEN).connect_timeout(300).read_timeout(300).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CallbackQueryHandler(button_callback))

    # Пересылка из группы и автоответы
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_reply))
    # Для пересылки медиа (фото/видео) из группы
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, forward_to_admin))

    print("Бот запущен и слушает сообщения...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
