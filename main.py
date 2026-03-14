import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import json
import os
import base64
from threading import Thread
 
import requests
from flask import Flask, jsonify, request, send_from_directory
 
BOT_TOKEN = '8232012309:AAHi2AVImeCLHlHs7oCVQeXhiKBvZj00JeY'
ADMIN_CHAT_ID = 8201066917
 
PORT = int(os.getenv('PORT', '8000'))
 
# Render сам выставляет RENDER_EXTERNAL_URL — подхватываем автоматически
WEB_APP_URL = (
    os.getenv('RENDER_EXTERNAL_URL') or
    os.getenv('WEB_APP_URL', 'http://localhost:8000')
)
 
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SUPPORTED_CRYPTOS = ['USDT', 'BTC', 'ETH', 'TON']
 
# ── GitHub (задать в Render → Environment) ──
# GITHUB_TOKEN  — Personal Access Token (scope: repo)
# GITHUB_REPO   — vlad49228/tgbot
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')
GITHUB_REPO  = os.getenv('GITHUB_REPO', 'vlad49228/tgbot')
GITHUB_FILE  = 'user_balances.json'
GITHUB_API   = f'https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}'
GITHUB_HEADERS = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json',
}
 
bot = telebot.TeleBot(BOT_TOKEN)
 
# ──────────────── Балансы через GitHub ────────────────
 
def load_balances():
    try:
        resp = requests.get(GITHUB_API, headers=GITHUB_HEADERS, timeout=10)
        if resp.status_code == 200:
            content = base64.b64decode(resp.json()['content']).decode('utf-8')
            return json.loads(content)
        print(f"GitHub load error: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"load_balances error: {e}")
    return {}
 
def save_balances(balances):
    try:
        resp = requests.get(GITHUB_API, headers=GITHUB_HEADERS, timeout=10)
        sha = resp.json().get('sha', '') if resp.status_code == 200 else ''
 
        content = base64.b64encode(
            json.dumps(balances, indent=2, ensure_ascii=False).encode('utf-8')
        ).decode('utf-8')
 
        r = requests.put(GITHUB_API, headers=GITHUB_HEADERS, json={
            'message': 'update balances',
            'content': content,
            'sha': sha,
        }, timeout=10)
 
        if r.status_code not in (200, 201):
            print(f"GitHub save error: {r.status_code} {r.text}")
    except Exception as e:
        print(f"save_balances error: {e}")
 
def get_user_balances(user_id):
    all_balances = load_balances()
    uid = str(user_id)
    if uid not in all_balances:
        all_balances[uid] = {c: 0.0 for c in SUPPORTED_CRYPTOS}
        save_balances(all_balances)
        print(f"Новый пользователь {uid}")
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
 
# ──────────────── Бот ────────────────
 
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    username = message.from_user.username or "нет юзернейма"
    first_name = message.from_user.first_name or ""
 
    balances = get_user_balances(user_id)
 
    bot.send_message(
        ADMIN_CHAT_ID,
        f"Новый пользователь запустил бота!\n"
        f"ID: {user_id}\n"
        f"Username: @{username}\n"
        f"Имя: {first_name}\n\n"
        f"Балансы:\n"
        f"USDT: {balances['USDT']}\n"
        f"BTC: {balances['BTC']}\n"
        f"ETH: {balances['ETH']}\n"
        f"TON: {balances['TON']}"
    )
 
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(
        text="Открыть Alpha Crypt",
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
            print(f"Пользователь {user_id} выбрал {data.get('crypto')}")
 
        elif action == 'withdraw':
            bot.send_message(ADMIN_CHAT_ID, f"Запрос на вывод от {user_id}\nАдрес: {data.get('address')}")
 
        elif action.startswith('nav_'):
            print(f"Навигация: {action.replace('nav_', '')}")
 
    except Exception as e:
        print(f"Ошибка в web_app_data: {e}")
 
# ──────────────── Запуск ────────────────
 
print(f"Web App URL: {WEB_APP_URL}")
 
# Бот в фоне, Flask — главный процесс (Render требует веб-сервер)
Thread(target=lambda: (bot.remove_webhook(), bot.infinity_polling()), daemon=True).start()
 
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
 
