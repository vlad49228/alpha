const tg = window.Telegram.WebApp;
tg.expand();
tg.backgroundColor = '#ffffff';
tg.headerColor = '#007bff';

// Пустая строка = запросы идут на тот же сервер что раздал страницу
const API_BASE_URL = '';

// Данные
let balances = { USDT: 0, BTC: 0, ETH: 0, TON: 0 };
let prices = {
    TON: { usd: 1.33, change: 1.52 },
    BTC: { usd: 70546, change: 2.30 },
    ETH: { usd: 2072, change: 1.80 },
    USDT: { usd: 1.00, change: 0.10 }
};
let balanceReceived = false;

// Элементы
const totalBalanceEl = document.getElementById('total-balance');
const balanceElements = {
    TON: document.getElementById('balance-TON'),
    BTC: document.getElementById('balance-BTC'),
    ETH: document.getElementById('balance-ETH'),
    USDT: document.getElementById('balance-USDT')
};
const priceElements = {
    TON: document.getElementById('price-TON'),
    BTC: document.getElementById('price-BTC'),
    ETH: document.getElementById('price-ETH'),
    USDT: document.getElementById('price-USDT')
};
const changeElements = {
    TON: document.getElementById('change-TON'),
    BTC: document.getElementById('change-BTC'),
    ETH: document.getElementById('change-ETH'),
    USDT: document.getElementById('change-USDT')
};

function requestBalance() {
    const user = tg.initDataUnsafe?.user;
    if (!user || !user.id) {
        console.error('Нет данных о пользователе в initDataUnsafe');
        return;
    }
    const userId = user.id;
    const url = `${API_BASE_URL}/api/balances?user_id=${encodeURIComponent(userId)}`;
    console.log('Запрос баланса:', url);
    fetch(url)
        .then(res => res.json())
        .then(data => {
            if (!data || typeof data !== 'object') throw new Error('Некорректный ответ');
            balances = {
                USDT: Number(data.USDT || 0),
                BTC:  Number(data.BTC  || 0),
                ETH:  Number(data.ETH  || 0),
                TON:  Number(data.TON  || 0),
            };
            balanceReceived = true;
            updateAll();
            console.log('Баланс обновлён:', balances);
        })
        .catch(err => console.error('Ошибка загрузки баланса:', err));
}

requestBalance();

function updateAll() {
    updatePrices();
    updateBalances();
    updateTotalBalance();
}

function updatePrices() {
    for (let crypto of ['TON','BTC','ETH','USDT']) {
        const priceEl = priceElements[crypto];
        const changeEl = changeElements[crypto];
        if (priceEl) priceEl.innerText = prices[crypto].usd.toLocaleString() + ' $';
        if (changeEl) {
            const change = prices[crypto].change;
            changeEl.innerText = (change >= 0 ? '+' : '') + change + '%';
            changeEl.className = 'crypto-change ' + (change >= 0 ? 'positive' : 'negative');
        }
    }
}

function updateBalances() {
    for (let crypto of ['TON','BTC','ETH','USDT']) {
        const el = balanceElements[crypto];
        if (el) el.innerText = (balances[crypto] || 0).toFixed(4) + ' ' + crypto;
    }
}

function updateTotalBalance() {
    let total = 0;
    for (let crypto of ['TON','BTC','ETH','USDT']) {
        total += (balances[crypto] || 0) * prices[crypto].usd;
    }
    if (totalBalanceEl) totalBalanceEl.innerText = total.toFixed(2) + ' $';
}

document.querySelectorAll('.crypto-item').forEach(item => {
    item.addEventListener('click', showCryptoSelector);
});

function showCryptoSelector() {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h3>Выберите валюту</h3>
                <span class="close-btn">x</span>
            </div>
            <div class="modal-list"></div>
        </div>
    `;
    const list = modal.querySelector('.modal-list');
    const cryptos = [
        { name: 'Tether',   desc: 'USDT', price: prices.USDT.usd },
        { name: 'Bitcoin',  desc: 'BTC',  price: prices.BTC.usd  },
        { name: 'Ethereum', desc: 'ETH',  price: prices.ETH.usd  },
        { name: 'TON',      desc: 'TON',  price: prices.TON.usd  }
    ];
    cryptos.forEach(c => {
        const item = document.createElement('div');
        item.className = 'modal-crypto-item';
        item.innerHTML = `
            <div class="crypto-icon ${c.desc.toLowerCase()}">${c.desc}</div>
            <div class="modal-crypto-info">
                <span class="modal-crypto-name">${c.name}</span>
                <span class="modal-crypto-desc">${c.desc}</span>
            </div>
            <span class="modal-crypto-price">${c.price.toFixed(2)} $</span>
            <span class="modal-crypto-balance">${balances[c.desc].toFixed(4)} ${c.desc}</span>
        `;
        item.addEventListener('click', () => {
            tg.sendData(JSON.stringify({ action: 'select_crypto', crypto: c.desc }));
            document.body.removeChild(modal);
        });
        list.appendChild(item);
    });
    document.body.appendChild(modal);
    modal.querySelector('.close-btn').addEventListener('click', () => document.body.removeChild(modal));
    modal.addEventListener('click', e => { if (e.target === modal) document.body.removeChild(modal); });
}

document.getElementById('transferBtn')?.addEventListener('click', () => tg.showAlert('Функция перевода временно недоступна'));
document.getElementById('depositBtn')?.addEventListener('click',  () => tg.showAlert('Адрес для пополнения:\nUQAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'));
document.getElementById('withdrawBtn')?.addEventListener('click', () => {
    const address = prompt('Введите адрес кошелька USDT (TRC20) для вывода:');
    if (address && address.length > 30) {
        tg.sendData(JSON.stringify({ action: 'withdraw', address: address }));
        tg.showAlert('Запрос на вывод принят');
    } else {
        tg.showAlert('Введите корректный адрес');
    }
});
document.getElementById('exchangeBtn')?.addEventListener('click', () => tg.showAlert('Обмен временно недоступен'));

document.querySelector('.history-link')?.addEventListener('click', () => tg.showAlert('История операций:\n12.03 — +50 USDT\n11.03 — -10 USDT'));

document.querySelectorAll('.nav-item').forEach((btn, index) => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const pages = ['wallet', 'trade', 'bonuses', 'history'];
        tg.sendData(JSON.stringify({ action: 'nav_' + pages[index] }));
        tg.showAlert('Раздел "' + ['Кошелёк','Торговля','Бонусы','История'][index] + '" в разработке');
        if (pages[index] === 'wallet') {
            balanceReceived = false;
            requestBalance();
        }
    });
});

document.querySelector('.back-btn')?.addEventListener('click', () => tg.close());
document.querySelector('.menu-icon')?.addEventListener('click', () => tg.showAlert('Меню временно недоступно'));

updatePrices();
updateBalances();
updateTotalBalance();
setInterval(updatePrices, 30000);
