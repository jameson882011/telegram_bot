import asyncio
import time
import threading
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    ContextTypes,
    CommandHandler,
    ConversationHandler,
    CallbackQueryHandler,
)

# ---------- КОНФИГУРАЦИЯ ----------
BOT_TOKEN = "8885379423:AAGbn9nfZj-I4_nzC0mU9Aec0y23GGbzaLY"
ADMIN_ID = 5206473963
CHAT_ID = -1003978554378
# ---------------------------------

NAME, PHONE, ADDRESS = range(3)

SERVICES_FILE = "services.json"
FAQ_FILE = "faq.json"
STATS_FILE = "stats.json"

def load_json(filename, default):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

services = load_json(SERVICES_FILE, [])
faq = load_json(FAQ_FILE, {})
stats = load_json(STATS_FILE, {"orders": 0, "messages": 0})

if not services:
    services = [
        {"name": "Покраска стен", "price": "от 500 ₽/м²", "photo": "https://i.imgur.com/your_painting.jpg", "desc": "Качественные краски, гарантия 5 лет."},
        {"name": "Штукатурка стен", "price": "от 800 ₽/м²", "photo": "https://i.imgur.com/your_plaster.jpg", "desc": "Идеально ровные стены под обои или покраску."},
        {"name": "Укладка плитки", "price": "от 1500 ₽/м²", "photo": "https://i.imgur.com/your_tile.jpg", "desc": "Для ванных, кухонь, прихожих."},
        {"name": "Натяжные потолки", "price": "от 700 ₽/м²", "photo": "https://i.imgur.com/your_ceiling.jpg", "desc": "Матовые, глянцевые, тканевые."},
        {"name": "Устранение косяков", "price": "от 2000 ₽/стену", "photo": "https://i.imgur.com/your_fix.jpg", "desc": "Убираем светотени, кривые углы, неровности."},
    ]
    save_json(SERVICES_FILE, services)

if not faq:
    faq = {
        "светотень": "Светотени на стенах возникают из-за неравномерного нанесения краски или плохой подготовки. Обычно помогает перекраска с валиком с длинным ворсом.",
        "штукатурка": "Штукатурка должна сохнуть минимум 7 дней перед покраской.",
        "потолок": "Для потолка лучше использовать матовую краску – она скрывает неровности.",
        "плитка": "Для ванной используйте влагостойкий клей и затирку с антигрибковыми добавками.",
        "цена": "Цены зависят от объёма и состояния поверхностей. Напишите мне в личные сообщения.",
        "сроки": "Обычно отделка квартиры 50 м² занимает 2–3 недели.",
    }
    save_json(FAQ_FILE, faq)

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

def get_service_keyboard(index, total):
    buttons = []
    if index > 0:
        buttons.append(InlineKeyboardButton("◀️ Назад", callback_data=f"svc_{index-1}"))
    if index < total - 1:
        buttons.append(InlineKeyboardButton("Вперёд ▶️", callback_data=f"svc_{index+1}"))
    buttons.append(InlineKeyboardButton("📋 В меню", callback_data="back"))
    return InlineKeyboardMarkup([buttons]) if buttons else get_back_menu()

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я бот-помощник по отделке.\n"
        "Выберите, что вам нужно:",
        reply_markup=get_main_menu()
    )
    stats["messages"] += 1
    save_json(STATS_FILE, stats)

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📋 Главное меню:", reply_markup=get_main_menu())

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "prices":
        context.user_data["service_index"] = 0
        await show_service(update, context, 0)
    elif data.startswith("svc_"):
        index = int(data.split("_")[1])
        await show_service(update, context, index)
    elif data == "order":
        context.user_data["order_step"] = "name"
        await query.edit_message_text(
            "📝 Для записи на замер напишите ваше **имя** (или /cancel для отмены)."
        )
        return
    elif data == "faq":
        text = "❓ **Готовые ответы:**\n\n"
        for keyword, answer in faq.items():
            text += f"• *{keyword.capitalize()}* — {answer}\n\n"
        text += "Если не нашли ответ, просто напишите свой вопрос."
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=get_back_menu())
    elif data == "report":
        await query.edit_message_text(
            "📸 Отправьте **фото или видео** проблемы, затем напишите текстовое описание.\n"
            "Я перешлю всё мастеру.",
            reply_markup=get_back_menu()
        )
        context.user_data["report_step"] = "waiting_media"
    elif data == "back":
        await query.edit_message_text("Главное меню:", reply_markup=get_main_menu())

async def show_service(update, context, index):
    query = update.callback_query
    service = services[index]
    caption = f"💰 **{service['name']}**\nЦена: {service['price']}\n\n{service['desc']}"
    keyboard = get_service_keyboard(index, len(services))
    await query.edit_message_caption(caption=caption, parse_mode="Markdown", reply_markup=keyboard)

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
        except Exception as e:
            print(f"Ошибка пересылки: {e}")

async def order_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text and not text.startswith('/'):
        context.user_data["order_name"] = text
        context.user_data["order_step"] = "phone"
        await update.message.reply_text("Отлично! Теперь напишите ваш **телефон**.")
    else:
        await update.message.reply_text("Пожалуйста, напишите ваше имя.")

async def order_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text and not text.startswith('/'):
        context.user_data["order_phone"] = text
        context.user_data["order_step"] = "address"
        await update.message.reply_text("Теперь напишите **адрес** (город, улица, дом).")
    else:
        await update.message.reply_text("Пожалуйста, напишите телефон.")

async def order_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text and not text.startswith('/'):
        address = text
        name = context.user_data.get("order_name", "не указано")
        phone = context.user_data.get("order_phone", "не указано")
        msg = f"🔔 **НОВАЯ ЗАЯВКА НА ЗАМЕР**\nИмя: {name}\nТелефон: {phone}\nАдрес: {address}"
        await context.bot.send_message(chat_id=ADMIN_ID, text=msg, parse_mode="Markdown")
        await update.message.reply_text("✅ Заявка принята! Мы свяжемся с вами в ближайшее время.", reply_markup=get_main_menu())
        stats["orders"] += 1
        save_json(STATS_FILE, stats)
        context.user_data.clear()
    else:
        await update.message.reply_text("Пожалуйста, напишите адрес.")

async def cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "order_step" in context.user_data:
        context.user_data.clear()
        await update.message.reply_text("Заявка отменена.", reply_markup=get_main_menu())
    else:
        await update.message.reply_text("У вас нет активной заявки.")

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        if context.user_data.get("report_step") == "waiting_media":
            if update.message.photo:
                file_id = update.message.photo[-1].file_id
            elif update.message.video:
                file_id = update.message.video.file_id
            else:
                await update.message.reply_text("Пожалуйста, отправьте фото или видео.")
                return
            context.user_data["media_file_id"] = file_id
            context.user_data["report_step"] = "waiting_description"
            await update.message.reply_text("📝 Теперь напишите текстовое описание проблемы.")
        else:
            await update.message.reply_text(
                "Чтобы сообщить о проблеме, нажмите кнопку «Показать проблему на фото» в меню.",
                reply_markup=get_main_menu()
            )

async def handle_report_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("report_step") == "waiting_description":
        description = update.message.text
        file_id = context.user_data.get("media_file_id")
        if file_id:
            caption = f"📸 **Проблема от пользователя**\nОписание: {description}"
            await context.bot.send_photo(chat_id=ADMIN_ID, photo=file_id, caption=caption, parse_mode="Markdown")
            await update.message.reply_text("✅ Отчёт отправлен мастеру! Он свяжется с вами.", reply_markup=get_main_menu())
            stats["messages"] += 1
            save_json(STATS_FILE, stats)
            context.user_data.clear()
        else:
            await update.message.reply_text("Ошибка. Попробуйте заново.")
            context.user_data.clear()

async def auto_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        text = update.message.text
        if text:
            text_lower = text.lower()
            for keyword, answer in faq.items():
                if keyword in text_lower:
                    await update.message.reply_text(answer)
                    stats["messages"] += 1
                    save_json(STATS_FILE, stats)
                    return
    if update.effective_chat.id == CHAT_ID:
        await forward_to_admin(update, context)

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("У вас нет прав на эту команду.")
        return
    msg = f"📊 **Статистика:**\nЗаявок: {stats['orders']}\nСообщений в бот: {stats['messages']}"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def admin_add_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Нет прав.")
        return
    args = update.message.text.split(maxsplit=1)
    if len(args) < 2:
        await update.message.reply_text("Формат: /add_service Название | Цена | Описание | ссылка_фото")
        return
    parts = args[1].split("|")
    if len(parts) < 4:
        await update.message.reply_text("Нужно 4 части: Название | Цена | Описание | ссылка_фото")
        return
    new_service = {
        "name": parts[0].strip(),
        "price": parts[1].strip(),
        "desc": parts[2].strip(),
        "photo": parts[3].strip(),
    }
    services.append(new_service)
    save_json(SERVICES_FILE, services)
    await update.message.reply_text("✅ Услуга добавлена!")

async def admin_add_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Нет прав.")
        return
    args = update.message.text.split(maxsplit=1)
    if len(args) < 2:
        await update.message.reply_text("Формат: /add_faq слово | ответ")
        return
    parts = args[1].split("|")
    if len(parts) < 2:
        await update.message.reply_text("Нужно: слово | ответ")
        return
    keyword = parts[0].strip().lower()
    answer = parts[1].strip()
    faq[keyword] = answer
    save_json(FAQ_FILE, faq)
    await update.message.reply_text("✅ FAQ добавлен!")

def main():
    thread = threading.Thread(target=run_health_server, daemon=True)
    thread.start()

    app = Application.builder() \
        .token(BOT_TOKEN) \
        .connect_timeout(300) \
        .read_timeout(300) \
        .build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("add_service", admin_add_service))
    app.add_handler(CommandHandler("add_faq", admin_add_faq))

    app.add_handler(CallbackQueryHandler(button_callback))

    order_handler = ConversationHandler(
        entry_points=[CommandHandler("order", order_name)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, order_name)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, order_phone)],
            ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, order_address)],
        },
        fallbacks=[CommandHandler("cancel", cancel_order)],
    )
    app.add_handler(order_handler)

    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_report_description))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_reply))

    print("Бот запущен и слушает сообщения...")
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
