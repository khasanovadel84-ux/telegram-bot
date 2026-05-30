import telebot
import time
import os
import traceback
import requests
from telebot import apihelper
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = os.getenv("BOT_TOKEN")
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
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
    "/about - о боте\n"
    "/status - статус бота\n"
    "/clear - забыть историю диалога\n\n"
    "Также просто напиши любой текст."
)
ABOUT_TEXT = "Я Telegram-бот на Python с ИИ-помощником (YandexGPT + pyTelegramBotAPI)."
BOT_VERSION = "v7-status"
HISTORY_LIMIT = 10

chat_history = {}


def log_info(message):
    print(f"[INFO] {message}", flush=True)


def log_error(message):
    print(f"[ERROR] {message}", flush=True)


def log_update(user, action):
    print(f"[UPDATE] {user_label(user)} → {action}", flush=True)


def get_history(chat_id):
    return chat_history.setdefault(chat_id, [])


def trim_history(history):
    if len(history) > HISTORY_LIMIT:
        del history[:-HISTORY_LIMIT]


def add_history(chat_id, role, text):
    history = get_history(chat_id)
    history.append({"role": role, "text": text})
    trim_history(history)


def clear_history(chat_id):
    chat_history.pop(chat_id, None)


def show_typing(chat_id):
    try:
        bot.send_chat_action(chat_id, "typing")
    except Exception:
        pass


def status_text(chat_id):
    ai = "включён" if YANDEX_API_KEY and YANDEX_FOLDER_ID else "выключен"
    count = len(get_history(chat_id))
    return (
        f"Статус бота\n\n"
        f"Версия: {BOT_VERSION}\n"
        f"ИИ (YandexGPT): {ai}\n"
        f"Сообщений в памяти: {count} из {HISTORY_LIMIT}\n\n"
        "Команда /clear — очистить память"
    )


def ask_ai(question, chat_id):
    if YANDEX_API_KEY and YANDEX_FOLDER_ID:
        try:
            messages = [
                {
                    "role": "system",
                    "text": "Ты дружелюбный Telegram-помощник. Отвечай кратко и понятно на русском языке.",
                },
            ]
            messages.extend(get_history(chat_id))
            messages.append({"role": "user", "text": question})

            response = requests.post(
                "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
                headers={
                    "Authorization": f"Api-Key {YANDEX_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt-lite/latest",
                    "completionOptions": {
                        "stream": False,
                        "temperature": 0.6,
                        "maxTokens": 500,
                    },
                    "messages": messages,
                },
                timeout=60,
            )
            response.raise_for_status()
            answer = response.json()["result"]["alternatives"][0]["message"]["text"].strip()
            return answer
        except Exception as e:
            log_error(f"YandexGPT: {e}")

    return None


def smart_reply(text, chat_id):
    normalized = text.lower().strip()

    greetings = ("привет", "здравствуй", "здравствуйте", "hi", "hello", "добрый день", "добрый вечер")
    if any(word in normalized for word in greetings):
        return "Привет! Рад вас видеть. Задайте любой вопрос — отвечу с помощью ИИ."

    if "как дела" in normalized or normalized in ("как ты", "как сам"):
        return "Всё отлично, спасибо! А у вас как?"

    if "спасибо" in normalized or "благодар" in normalized:
        return "Пожалуйста! Рад помочь."

    if normalized in ("пока", "до свидания", "bye", "goodbye"):
        return "До встречи! Напишите, если понадоблюсь."

    show_typing(chat_id)
    ai_answer = ask_ai(text, chat_id)
    if ai_answer:
        add_history(chat_id, "user", text)
        add_history(chat_id, "assistant", ai_answer)
        return ai_answer

    if not YANDEX_API_KEY or not YANDEX_FOLDER_ID:
        return (
            f'Я получил: "{text}"\n\n'
            "ИИ пока не подключен. Добавьте YANDEX_API_KEY и YANDEX_FOLDER_ID в GitHub Secrets."
        )

    return f'Не удалось получить ответ от ИИ. Попробуйте переформулировать вопрос: "{text}"'

@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        log_update(message.from_user, "/start")
        bot.reply_to(
            message,
            "Привет! Я твой ИИ-помощник.\n\n"
            f"Версия: {BOT_VERSION}\n"
            "Нажми кнопки прямо под этим сообщением 👇",
            reply_markup=inline_keyboard()
        )
        bot.send_message(
            message.chat.id,
            "Быстрые кнопки также доступны внизу 👇",
            reply_markup=main_keyboard()
        )
    except Exception as e:
        log_error(f"/start: {e}")


@bot.message_handler(commands=['help'])
def send_help(message):
    try:
        log_update(message.from_user, "/help")
        bot.reply_to(message, HELP_TEXT, reply_markup=inline_keyboard())
    except Exception as e:
        log_error(f"/help: {e}")


@bot.message_handler(commands=['about'])
def send_about(message):
    try:
        log_update(message.from_user, "/about")
        bot.reply_to(message, ABOUT_TEXT, reply_markup=inline_keyboard())
    except Exception as e:
        log_error(f"/about: {e}")


@bot.message_handler(commands=['clear'])
def send_clear(message):
    try:
        log_update(message.from_user, "/clear")
        clear_history(message.chat.id)
        bot.reply_to(message, "История диалога очищена. Можете начать новый разговор.")
    except Exception as e:
        log_error(f"/clear: {e}")


@bot.message_handler(commands=['status'])
def send_status(message):
    try:
        log_update(message.from_user, "/status")
        bot.reply_to(message, status_text(message.chat.id), reply_markup=inline_keyboard())
    except Exception as e:
        log_error(f"/status: {e}")


@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_text(message):
    try:
        text = (message.text or "").strip()
        log_update(message.from_user, text[:60])

        if text in ("Помощь", "📋 Помощь"):
            send_help(message)
            return
        if text in ("О боте", "ℹ️ О боте"):
            send_about(message)
            return
        if text in ("Задать вопрос", "💬 Задать вопрос"):
            bot.reply_to(message, "Напиши свой вопрос одним сообщением — я отвечу.")
            return

        bot.reply_to(message, smart_reply(text, message.chat.id), reply_markup=inline_keyboard())
    except Exception as e:
        log_error(f"text: {e}")


@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    try:
        log_update(call.from_user, f"кнопка:{call.data}")
        bot.answer_callback_query(call.id)

        if call.data == "help":
            bot.send_message(call.message.chat.id, HELP_TEXT, reply_markup=inline_keyboard())
        elif call.data == "about":
            bot.send_message(call.message.chat.id, ABOUT_TEXT, reply_markup=inline_keyboard())
        elif call.data == "ask":
            bot.send_message(call.message.chat.id, "Напиши свой вопрос одним сообщением — я отвечу.")
    except Exception as e:
        log_error(f"callback: {e}")

if __name__ == "__main__":
    ai_status = "YandexGPT включен" if YANDEX_API_KEY and YANDEX_FOLDER_ID else "ИИ выключен"
    log_info(f"Старт {BOT_VERSION}, {ai_status}")
    while True:
        try:
            me = bot.get_me()
            log_info(f"Бот @{me.username} онлайн, ожидаю сообщения")
            bot.remove_webhook()
            time.sleep(1)
            bot.infinity_polling(
                timeout=30,
                long_polling_timeout=30,
                skip_pending=True,
                allowed_updates=["message", "callback_query"]
            )
        except Exception as e:
            log_error(f"Падение: {e}")
            print(traceback.format_exc(), flush=True)
            log_info("Перезапуск через 5 секунд...")
            time.sleep(5)