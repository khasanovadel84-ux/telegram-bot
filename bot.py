import telebot
import time
import os
import traceback
from telebot import apihelper

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


def user_tag(message):
    return f"@{message.from_user.username}" if message.from_user.username else f"id={message.from_user.id}"

@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        print(f"[UPDATE] /start от {user_tag(message)} (chat={message.chat.id})", flush=True)
        bot.reply_to(
            message,
            "Привет! Я твой ИИ-помощник.\n\n"
            "Доступные команды:\n"
            "/help - список команд\n"
            "/about - информация о боте"
        )
    except Exception as e:
        print(f"[ERROR] Ошибка в /start handler: {e}", flush=True)


@bot.message_handler(commands=['help'])
def send_help(message):
    try:
        print(f"[UPDATE] /help от {user_tag(message)} (chat={message.chat.id})", flush=True)
        bot.reply_to(
            message,
            "Команды:\n"
            "/start - приветствие\n"
            "/help - помощь\n"
            "/about - о боте\n\n"
            "Также просто напиши любой текст."
        )
    except Exception as e:
        print(f"[ERROR] Ошибка в /help handler: {e}", flush=True)


@bot.message_handler(commands=['about'])
def send_about(message):
    try:
        print(f"[UPDATE] /about от {user_tag(message)} (chat={message.chat.id})", flush=True)
        bot.reply_to(message, "Я Telegram-бот на Python (pyTelegramBotAPI).")
    except Exception as e:
        print(f"[ERROR] Ошибка в /about handler: {e}", flush=True)


@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_text(message):
    try:
        print(f"[UPDATE] Текст от {user_tag(message)} (chat={message.chat.id}): {message.text}", flush=True)
        bot.reply_to(message, "Я получил сообщение!")
    except Exception as e:
        print(f"[ERROR] Ошибка в text handler: {e}", flush=True)

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
                allowed_updates=["message"]
            )
        except Exception as e:
            print(f"[ERROR] Бот упал с ошибкой подключения/работы: {e}", flush=True)
            print(traceback.format_exc(), flush=True)
            print("[INFO] Повторный запуск через 5 секунд...", flush=True)
            time.sleep(5)
        finally:
            print("[INFO] Цикл polling завершен.", flush=True)