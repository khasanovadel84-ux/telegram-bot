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
ABOUT_TEXT = "Я Telegram-бот на Python с ИИ-помощником (YandexGPT + pyTelegramBotAPI)."
BOT_VERSION = "v4-yandex"


def ask_ai(question):
    if YANDEX_API_KEY and YANDEX_FOLDER_ID:
        try:
            print(f"[INFO] Запрос к YandexGPT: {question[:80]}...", flush=True)
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
                    "messages": [
                        {
                            "role": "system",
                            "text": "Ты дружелюбный Telegram-помощник. Отвечай кратко и понятно на русском языке.",
                        },
                        {"role": "user", "text": question},
                    ],
                },
                timeout=60,
            )
            response.raise_for_status()
            answer = response.json()["result"]["alternatives"][0]["message"]["text"].strip()
            print("[INFO] YandexGPT ответил успешно", flush=True)
            return answer
        except Exception as e:
            print(f"[ERROR] Ошибка YandexGPT: {e}", flush=True)

    return None


def smart_reply(text):
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

    ai_answer = ask_ai(text)
    if ai_answer:
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
        print(f"[UPDATE] /start от {user_tag(message)} (chat={message.chat.id})", flush=True)
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

        bot.reply_to(message, smart_reply(text), reply_markup=inline_keyboard())
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
    print(f"[INFO] Запускаю Telegram-бота ({BOT_VERSION})...", flush=True)
    if YANDEX_API_KEY and YANDEX_FOLDER_ID:
        print("[INFO] ИИ включен (YandexGPT)", flush=True)
    else:
        print("[INFO] ИИ выключен — добавьте YANDEX_API_KEY и YANDEX_FOLDER_ID", flush=True)
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