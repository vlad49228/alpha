import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import json
import os
import re
import subprocess
import time
from threading import Thread

from flask import Flask, jsonify, request, send_from_directory

BOT_TOKEN = '8232012309:AAFEaushvc8QsXMVmmjLTmcmG05cohtH7cQ'
ADMIN_CHAT_ID = 8201066917

PORT = int(os.getenv('PORT', '8000'))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BALANCE_FILE = os.path.join(BASE_DIR, 'user_balances.json')
SUPPORTED_CRYPTOS = ['USDT', 'BTC', 'ETH', 'TON']

bot = telebot.TeleBot(BOT_TOKEN)
WEB_APP_URL = ''

# ──────────────── Балансы ────────────────

def load_balances():
    try:
        if os.path.exists(BALANCE_FILE):
            with open(BALANCE_FILE, 'r', encoding='utf-8') as f:
                data = f.read().strip()
                return json.loads(data) if data else {}
    except Exception as e:
        print(f"load_balances error: {e}")
    return {}

def save_balances(balances):
    try:
        with open(BALANCE_FILE, 'w', encoding='utf-8') as f:
            json.dump(balances, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"save_balances error: {e}")

def get_user_balances(user_id):
    all_balances = load_balances()
    uid = str(user_id)
    if uid not in all_balances:
        all_balances[uid] = {c: 0.0 for c in SUPPORTED_CRYPTOS}
        save_balances(all_balances)
        print(f"➕ Новый пользователь {uid}")
    return all_balances[uid]

# ──────────────── Flask ────────────────

app = Flask(__name__)

@app.route('/')
def serve_index():
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(BASE_DIR, filename)

@app.route('/api/balances', methods=['GET'])
def api_get_balances():
    user_id = request.args.get('user_id')
    if not user_id:
        resp = jsonify({'error': 'user_id is required'})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 400
    balances = get_user_balances(user_id)
    resp = jsonify(balances)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

# ──────────────── Cloudflare Tunnel ────────────────

def start_cloudflared():
    """
    Запускает cloudflared quick tunnel и возвращает публичный HTTPS URL.
    Скачать cloudflared: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/
    Windows: поместить cloudflared.exe рядом с main.py или добавить в PATH.
    """
    # Ищем cloudflared рядом с main.py, потом в PATH
    local_bin = os.path.join(BASE_DIR, 'cloudflared.exe') if os.name == 'nt' else os.path.join(BASE_DIR, 'cloudflared')
    binary = local_bin if os.path.exists(local_bin) else 'cloudflared'

    proc = subprocess.Popen(
        [binary, 'tunnel', '--url', f'http://localhost:{PORT}'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    url = None
    for line in proc.stdout:
        print(f"[cloudflared] {line.rstrip()}")
        match = re.search(r'https://[a-zA-Z0-9\-]+\.trycloudflare\.com', line)
        if match:
            url = match.group(0)
            break

    if not url:
        raise RuntimeError("Не удалось получить URL от cloudflared. Убедитесь что cloudflared установлен.")

    # Продолжаем читать вывод в фоне чтобы процесс не завис
    Thread(target=lambda: [proc.stdout.read()], daemon=True).start()
    return url

# ──────────────── Бот ────────────────

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    username = message.from_user.username or "нет юзернейма"
    first_name = message.from_user.first_name or ""

    balances = get_user_balances(user_id)

    bot.send_message(
        ADMIN_CHAT_ID,
        f"🆕 Новый пользователь запустил бота!\n"
        f"ID: {user_id}\n"
        f"Username: @{username}\n"
        f"Имя: {first_name}\n\n"
        f"💰 Балансы пользователя {user_id}:\n"
        f"💵 Tether (USDT): {balances['USDT']} $\n"
        f"₿ Bitcoin (BTC): {balances['BTC']} BTC\n"
        f"⟠ Ethereum (ETH): {balances['ETH']} ETH\n"
        f"⚡ TON: {balances['TON']} TON"
    )

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(
        text="🚀 Открыть крипто-дашборд",
        web_app=WebAppInfo(url=WEB_APP_URL)
    ))

    bot.send_message(
        user_id,
        "Добро пожаловать в Alpha Crypt.\n\n"
        "Alpha Crypt — это открытая криптобиржа, созданная для тех, кто ценит прозрачность и свободу. "
        "Весь код проекта находится в открытом доступе — любой желающий может проверить, как именно работает платформа, "
        "как хранятся данные и как исполняются сделки. Никаких скрытых механизмов и закрытых алгоритмов.\n\n"
        "На платформе доступна торговля основными активами: Bitcoin, Ethereum, TON и Tether. "
        "Вы можете пополнять счёт, выводить средства и обменивать активы между собой — всё это прямо внутри Telegram, "
        "без необходимости переходить на сторонние сайты или устанавливать дополнительные приложения.\n\n"
        "Alpha Crypt не требует верификации личности. Для начала работы достаточно просто открыть кошелёк. "
        "Ваши средства остаются под вашим контролем на всех этапах.\n\n"
        "Нажмите кнопку ниже, чтобы войти в личный кабинет.",
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.message_handler(content_types=['web_app_data'])
def handle_web_app_data(message):
    try:
        data = json.loads(message.web_app_data.data)
        action = data.get('action')
        user_id = message.chat.id

        if action == 'get_balances':
            balances = get_user_balances(user_id)
            bot.send_message(user_id, f"BALANCES_DATA:{json.dumps(balances)}")

        elif action == 'select_crypto':
            crypto = data.get('crypto')
            print(f"🪙 Пользователь {user_id} выбрал {crypto}")

        elif action == 'withdraw':
            address = data.get('address')
            bot.send_message(ADMIN_CHAT_ID, f"💰 Запрос на вывод от {user_id}\nАдрес: {address}")

        elif action.startswith('nav_'):
            page = action.replace('nav_', '')
            print(f"📱 Навигация: {page}")

    except Exception as e:
        print(f"Ошибка в web_app_data: {e}")

# ──────────────── Запуск ────────────────

if __name__ == '__main__':
    print("🚀 Запуск бота и API...")

    if not os.path.exists(BALANCE_FILE):
        save_balances({})
        print("✅ Файл балансов создан")

    # Стартуем Flask в фоне
    def run_api():
        print(f"⚙️  Flask на порту {PORT}")
        app.run(host='0.0.0.0', port=PORT, use_reloader=False)

    api_thread = Thread(target=run_api, daemon=True)
    api_thread.start()
    time.sleep(1)  # даём Flask подняться

    # Получаем публичный HTTPS URL через cloudflared (без аккаунта)
    WEB_APP_URL = start_cloudflared()
    print(f"🌐 Публичный URL (Web App): {WEB_APP_URL}")

    bot.remove_webhook()
    print("✅ Бот готов. Запуск long polling.")
    bot.infinity_polling()
