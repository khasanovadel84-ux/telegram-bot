import telebot
import time
import os
import traceback
from telebot import apihelper
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("Не задан BOT_TOKEN. Добавь токен бота в переменные окружения.")

bot = telebot.TeleBot(BOT_TOKEN)

# Leave empty for direct connection, or set proxy URL.
PROXY_URL = ""

# Env var has priority, then PROXY_URL from code.
proxy = os.getenv("TELEGRAM_PROXY") or PROXY_URL
if proxy:
    apihelper.proxy = {"https": proxy, "http": proxy}
    print(f"[INFO] Использую прокси: {proxy}", flush=True)


def user_label(user):
    return f"@{user.username}" if user.username else f"id={user.id}"


def user_tag(message):
    return user_label(message.from_user)


def main_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton("Помощь"), KeyboardButton("О боте"))
    markup.row(KeyboardButton("Задать вопрос"))
    return markup


def inline_keyboard():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("Помощь", callback_data="help"),
        InlineKeyboardButton("О боте", callback_data="about"),
    )
    markup.row(InlineKeyboardButton("Задать вопрос", callback_data="ask"))
    return markup


HELP_TEXT = (
    "Команды:\n"
    "/start - приветствие\n"
    "/help - помощь\n"
    "/about - о боте\n\n"
    "Также просто напиши любой текст."
)
ABOUT_TEXT = "Я Telegram-бот на Python (pyTelegramBotAPI)."

@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        print(f"[UPDATE] /start от {user_tag(message)} (chat={message.chat.id})", flush=True)
        bot.reply_to(
            message,
            "Привет! Я твой ИИ-помощник.\n\n"
            "Нажми кнопки под этим сообщением\n"
            "или используй клавиатуру внизу экрана.",
            reply_markup=inline_keyboard()
        )
        bot.send_message(
            message.chat.id,
            "Быстрые кнопки также доступны внизу 👇",
            reply_markup=main_keyboard()
        )
        print("[INFO] Кнопки отправлены", flush=True)
    except Exception as e:
        print(f"[ERROR] Ошибка в /start handler: {e}", flush=True)


@bot.message_handler(commands=['help'])
def send_help(message):
    try:
        print(f"[UPDATE] /help от {user_tag(message)} (chat={message.chat.id})", flush=True)
        bot.reply_to(message, HELP_TEXT, reply_markup=inline_keyboard())
    except Exception as e:
        print(f"[ERROR] Ошибка в /help handler: {e}", flush=True)


@bot.message_handler(commands=['about'])
def send_about(message):
    try:
        print(f"[UPDATE] /about от {user_tag(message)} (chat={message.chat.id})", flush=True)
        bot.reply_to(message, ABOUT_TEXT, reply_markup=inline_keyboard())
    except Exception as e:
        print(f"[ERROR] Ошибка в /about handler: {e}", flush=True)


@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_text(message):
    try:
        print(f"[UPDATE] Текст от {user_tag(message)} (chat={message.chat.id}): {message.text}", flush=True)
        text = (message.text or "").strip()

        if text in ("Помощь", "📋 Помощь"):
            send_help(message)
            return
        if text in ("О боте", "ℹ️ О боте"):
            send_about(message)
            return
        if text in ("Задать вопрос", "💬 Задать вопрос"):
            bot.reply_to(message, "Напиши свой вопрос одним сообщением — я отвечу.")
            return

        bot.reply_to(message, "Я получил сообщение!")
    except Exception as e:
        print(f"[ERROR] Ошибка в text handler: {e}", flush=True)


@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    try:
        tag = user_label(call.from_user)
        print(f"[UPDATE] Кнопка: {call.data} от {tag}", flush=True)
        bot.answer_callback_query(call.id)

        if call.data == "help":
            bot.send_message(call.message.chat.id, HELP_TEXT, reply_markup=inline_keyboard())
        elif call.data == "about":
            bot.send_message(call.message.chat.id, ABOUT_TEXT, reply_markup=inline_keyboard())
        elif call.data == "ask":
            bot.send_message(call.message.chat.id, "Напиши свой вопрос одним сообщением — я отвечу.")
    except Exception as e:
        print(f"[ERROR] Ошибка в callback handler: {e}", flush=True)

if __name__ == "__main__":
    print("[INFO] Запускаю Telegram-бота...", flush=True)
    while True:
        try:
            me = bot.get_me()
            print(f"[INFO] Подключение успешно. Бот: @{me.username} (id={me.id})", flush=True)
            # If webhook was configured before, polling will not receive updates.
            bot.remove_webhook()
            time.sleep(1)
            print("[INFO] Webhook удален. Включаю long polling...", flush=True)
            print("[INFO] Бот ожидает сообщения...", flush=True)
            bot.infinity_polling(
                timeout=30,
                long_polling_timeout=30,
                skip_pending=True,
                allowed_updates=["message", "callback_query"]
            )
        except Exception as e:
            print(f"[ERROR] Бот упал с ошибкой подключения/работы: {e}", flush=True)
            print(traceback.format_exc(), flush=True)
            print("[INFO] Повторный запуск через 5 секунд...", flush=True)
            time.sleep(5)
        finally:
            print("[INFO] Цикл polling завершен.", flush=True)