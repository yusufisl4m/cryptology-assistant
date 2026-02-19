import os
import asyncio
import logging
import io # Resim dosyası işlemleri için
from datetime import datetime
import matplotlib.pyplot as plt # Grafik çizimi için
import matplotlib.dates as mdates # Tarih formatı için
from aiohttp import web

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
import aiohttp
import database

# --- RENDER İÇİN KRİTİK AYAR ---
# Sunucuda ekran olmadığı için 'Agg' modunu kullanıyoruz. Yoksa hata verir.
plt.switch_backend('Agg')

# 1. AYARLAR
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# Geçici Hafıza
USER_STATES = {}
TEMP_DATA = {} 

# --- DİL SÖZLÜĞÜ ---
TEXTS = {
    "tr": {
        "welcome_title": "🏆 CRYPTOLOGY 🏆",
        "select_lang": "Lütfen dil seçiniz / Please select language:",
        "menu_msg": "Hoş geldiniz! Menü aşağıda sabitlenmiştir.",
        "btn_market": "📈 Piyasalar",
        "btn_wallet": "👛 Cüzdanım",
        "btn_alarm": "🚨 Alarmlar",
        "btn_settings": "⚙️ Ayarlar",
        "settings_title": "⚙️ **AYARLAR MENÜSÜ**\nLütfen düzenlemek istediğiniz alanı seçin:",
        "set_market": "📈 Piyasa Ayarları",
        "set_wallet": "👛 Cüzdan Yönetimi",
        "set_alarm": "🚨 Alarm Ayarları",
        "set_lang": "🌐 Dil / Language",
        "set_info": "ℹ️ Bilgi",
        "back": "🔙 Geri",
        "add": "➕ Ekle",
        "del": "➖ Çıkart",
        "fav_empty": "⚠️ Listeniz boş! Ayarlardan ekleme yapabilirsiniz.",
        "enter_symbol": "✍️ Lütfen Coin sembolünü yazın (Örn: BTC):",
        "enter_amount_add": "✍️ Eklenecek miktarı yazın (Örn: 0.5):",
        "enter_amount_del": "✍️ Çıkartılacak miktarı yazın (Örn: 0.2):",
        "success_add": "✅ {} cüzdanınıza eklendi! (Yeni Bakiye: {})",
        "success_del": "🗑️ {} cüzdanınızdan düşüldü! (Kalan: {})",
        "success_update": "✅ Liste güncellendi: **{}**",
        "info_msg": (
            "ℹ️ **CRYPTOLOGY KULLANIM KILAVUZU**\n\n"
            "🔍 **Hızlı Fiyat & Grafik:**\n"
            "Herhangi bir coinin grafiğini görmek için sohbet satırına /btc, /eth, /sol gibi komutlar yazın.\n\n"
            "🎛 **Menü Özellikleri:**\n"
            "• Piyasalar: Ayarlardan eklediğiniz favori coinlerinizi listeler.\n"
            "• Cüzdanım: Varlıklarınızı hesaplar. (Ekleme/Çıkarma Ayarlar menüsünden yapılır)\n"
            "• Alarmlar: Seçtiğiniz coinlerde %1 ani hareket olursa bildirir.\n"
        ),
        "fng_title": "🧠 **PİYASA RUH HALİ**",
        "alarm_hit": "🚨 **ALARM: {}**\n{} %{:.2f}\n💰 Fiyat: ${}",
        "chart_caption": "📊 {} - 24 Saatlik Grafik\n💰 Fiyat: ${:,.2f}"
    },
    "en": {
        "welcome_title": "🏆 CRYPTOLOGY 🏆",
        "select_lang": "Please select language:",
        "menu_msg": "Welcome! The menu is pinned below.",
        "btn_market": "📈 Markets",
        "btn_wallet": "👛 My Wallet",
        "btn_alarm": "🚨 Alarms",
        "btn_settings": "⚙️ Settings",
        "settings_title": "⚙️ **SETTINGS MENU**\nSelect an option to customize:",
        "set_market": "📈 Market Settings",
        "set_wallet": "👛 Wallet Manager",
        "set_alarm": "🚨 Alarm Settings",
        "set_lang": "🌐 Language",
        "set_info": "ℹ️ Info",
        "back": "🔙 Back",
        "add": "➕ Add",
        "del": "➖ Remove",
        "fav_empty": "⚠️ List is empty! Add coins from Settings.",
        "enter_symbol": "✍️ Please type Coin symbol (e.g. BTC):",
        "enter_amount_add": "✍️ Enter amount to add (e.g. 0.5):",
        "enter_amount_del": "✍️ Enter amount to remove (e.g. 0.2):",
        "success_add": "✅ {} added to wallet! (New Total: {})",
        "success_del": "🗑️ {} removed from wallet! (Remaining: {})",
        "success_update": "✅ List updated: **{}**",
        "info_msg": (
            "ℹ️ **CRYPTOLOGY USER GUIDE**\n\n"
            "🔍 **Quick Price & Chart:**\n"
            "Type commands like /btc, /eth to see instant price and 24h chart.\n\n"
            "🎛 **Features:**\n""• Markets: Lists your favorite coins.\n"
            "• Wallet: Calculates portfolio value.\n"
            "• Alarms: Notifies on %1 price moves.\n"
        ),
        "fng_title": "🧠 **MARKET SENTIMENT**",
        "alarm_hit": "🚨 **ALERT: {}**\n{} %{:.2f}\n💰 Price: ${}",
        "chart_caption": "📊 {} - 24h Chart\n💰 Price: ${:,.2f}"
    }
}

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()
database.init_db()

# --- YARDIMCILAR ---
def get_t(user_id, key):
    lang = database.get_language(user_id) or "tr"
    return TEXTS[lang].get(key, key)

async def get_price(symbol):
    try:
        url = "https://api.binance.com/api/v3/ticker/price"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params={"symbol": f"{symbol.upper()}USDT"}) as resp:
                if resp.status == 200: return float((await resp.json())['price'])
    except: return None

async def get_fng():
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get("https://api.alternative.me/fng/?limit=1") as r:
                return (await r.json())['data'][0] if r.status == 200 else None
    except: return None

# --- GRAFİK MOTORU ---
async def generate_chart(symbol):
    try:
        # Binance'den son 24 saatin verisini al (1 saatlik mumlar - 24 adet)
        url = "https://api.binance.com/api/v3/klines"
        params = {"symbol": f"{symbol.upper()}USDT", "interval": "1h", "limit": 24}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                if resp.status != 200: return None
                data = await resp.json()

        # Veriyi işle (Zaman ve Kapanış Fiyatı)
        prices = [float(x[4]) for x in data]
        times = [datetime.fromtimestamp(x[0]/1000) for x in data]

        # Grafiği Çiz
        plt.figure(figsize=(10, 5), facecolor='#1e1e1e') # Koyu tema arka plan
        ax = plt.axes()
        ax.set_facecolor('#1e1e1e')
        
        # Çizgi rengi (Yükseliş yeşil, düşüş kırmızı)
        color = '#00ff88' if prices[-1] >= prices[0] else '#ff4d4d'
        plt.plot(times, prices, color=color, linewidth=2)
        
        # Detaylar
        plt.title(f"{symbol.upper()}/USDT (24h)", color='white', fontsize=14)
        plt.grid(True, color='#333333', linestyle='--')
        plt.xticks(color='white')
        plt.yticks(color='white')
        
        # Tarih formatı
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        
        # Resim olarak kaydet (RAM'e)
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        plt.close() # Temizle
        
        return buf
    except Exception as e:
        print(f"Chart Error: {e}")
        return None

# --- KLAVYELER ---
def main_menu_kb(user_id):
    t = lambda k: get_t(user_id, k)
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=t("btn_market")), KeyboardButton(text=t("btn_wallet"))],
        [KeyboardButton(text=t("btn_alarm")), KeyboardButton(text=t("btn_settings"))]
    ], resize_keyboard=True, persistent=True)

def settings_kb(user_id):
    t = lambda k: get_t(user_id, k)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("set_market"), callback_data="conf_market"),
         InlineKeyboardButton(text=t("set_wallet"), callback_data="conf_wallet")],
        [InlineKeyboardButton(text=t("set_alarm"), callback_data="conf_alarm"),
         InlineKeyboardButton(text=t("set_lang"), callback_data="conf_lang")],
        [InlineKeyboardButton(text=t("set_info"), callback_data="conf_info")]
    ])

def action_kb(user_id, mode):
    t = lambda k: get_t(user_id, k)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("add"), callback_data=f"add_{mode}"),
         InlineKeyboardButton(text=t("del"), callback_data=f"del_{mode}")],
        [InlineKeyboardButton(text=t("back"), callback_data="back_settings")]
    ])

# --- 1.BAŞLANGIÇ (/start) ---
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(TEXTS["tr"]["welcome_title"])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇹🇷 Türkçe", callback_data="lang_tr"),
         InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")]
    ])
    await message.answer(TEXTS["tr"]["select_lang"], reply_markup=kb)

# --- 2. DİL SEÇİMİ VE ANA MENÜ ---
@dp.callback_query(F.data.startswith("lang_"))
async def set_lang(call: CallbackQuery):
    lang = call.data.split("_")[1]
    database.set_language(call.from_user.id, lang)
    await call.message.delete()
    await call.message.answer(get_t(call.from_user.id, "menu_msg"), 
                              reply_markup=main_menu_kb(call.from_user.id))

# --- 3. ANA MENÜ BUTONLARI ---
@dp.message(F.text)
async def reply_handler(message: Message):
    uid = message.from_user.id
    txt = message.text
    t = lambda k: get_t(uid, k)
    state = USER_STATES.get(uid)
    
    # --- DURUM YÖNETİMİ (VERİ GİRİŞİ) ---
    if state:
        if txt.startswith("/"): return 
        
        # Piyasa & Alarm Ekleme/Çıkarma (Basit Liste)
        if state in ["wait_market_add", "wait_alarm_add"]:
            func = database.add_market_fav if "market" in state else database.add_alarm_fav
            func(uid, txt)
            await message.answer(t("success_update").format(txt.upper()))
        
        elif state in ["wait_market_del", "wait_alarm_del"]:
            func = database.del_market_fav if "market" in state else database.del_alarm_fav
            func(uid, txt)
            await message.answer(t("success_update").format(txt.upper()))

        # Cüzdan Sembolü Girişi
        elif state == "wait_wallet_symbol":
            TEMP_DATA[uid] = {"symbol": txt.upper()}
            # Hangi moddayız? (Ekleme mi Çıkarma mı?)
            mode = TEMP_DATA.get(f"{uid}_mode")
            
            if mode == "add":
                USER_STATES[uid] = "wait_wallet_amount_add"
                await message.answer(t("enter_amount_add"))
            else:
                USER_STATES[uid] = "wait_wallet_amount_del"
                await message.answer(t("enter_amount_del"))
            return 

        # Cüzdan Miktar Girişi (EKLEME)
        elif state == "wait_wallet_amount_add":
            try:
                amount = float(txt)
                symbol = TEMP_DATA[uid]["symbol"]
                # Mevcut bakiyeyi al ve üzerine ekle
                current = database.get_single_coin_amount(uid, symbol)
                new_total = current + amount
                
                database.update_wallet(uid, symbol, new_total)
                await message.answer(t("success_add").format(symbol, new_total))
            except:
                await message.answer("❌ Invalid number!")
        
        # Cüzdan Miktar Girişi (ÇIKARMA)
        elif state == "wait_wallet_amount_del":
            try:
                amount = float(txt)
                symbol = TEMP_DATA[uid]["symbol"]
                # Mevcut bakiyeden düş
                current = database.get_single_coin_amount(uid, symbol)
                new_total = current - amount
                
                if new_total < 0: new_total = 0 # Eksiye düşemez
                
                database.update_wallet(uid, symbol, new_total)
                await message.answer(t("success_del").format(symbol, new_total))
            except:
                await message.answer("❌ Invalid number!")

        USER_STATES[uid] = None # Durumu bitir
        return

    # --- KOMUT YAKALAYICI (/BTC vb.) ---
    if txt.startswith("/") and not txt.startswith("/start"):
        symbol = txt[1:].upper() # "/" işaretini at
        
        # Kullanıcıya "Grafik çiziliyor..." mesajı ver
        wait_msg = await message.answer(f"🎨 {symbol} {t('fetching')}")
        
        price = await get_price(symbol)
        if price:
            # Grafiği oluştur
            chart_img = await generate_chart(symbol)
            if chart_img:# Resmi gönder
                await message.answer_photo(
                    BufferedInputFile(chart_img.read(), filename=f"{symbol}.png"),
                    caption=t("chart_caption").format(symbol, price)
                )
                await wait_msg.delete() # Bekleyiniz mesajını sil
            else:
                await wait_msg.edit_text(f"💰 {symbol}: ${price:,.2f} (No Chart)")
        else:
            await wait_msg.edit_text(t("fav_empty")) # Bulunamadı mesajı
        return

    # --- MENÜ TIKLAMALARI ---
    if txt in [TEXTS["tr"]["btn_settings"], TEXTS["en"]["btn_settings"]]:
        await message.answer(t("settings_title"), reply_markup=settings_kb(uid))

    elif txt in [TEXTS["tr"]["btn_market"], TEXTS["en"]["btn_market"]]:
        favs = database.get_market_favs(uid)
        if not favs:
            await message.answer(t("fav_empty"))
            return
        
        msg = await message.answer("⏳ ...")
        report = f"{t('btn_market')}\n──────────────\n"
        for coin in favs:
            p = await get_price(coin)
            report += f"🔹 {coin}: ${p:,.2f}\n" if p else f"⚠️ {coin}: --\n"
        
        fng = await get_fng()
        if fng: report += f"\n{t('fng_title')}: {fng['value']} ({fng['value_classification']})"
        await msg.edit_text(report)

    elif txt in [TEXTS["tr"]["btn_wallet"], TEXTS["en"]["btn_wallet"]]:
        wallet = database.get_wallet(uid)
        if not wallet:
            await message.answer(t("fav_empty"))
            return
        
        msg = await message.answer("⏳ ...")
        total = 0
        report = f"{t('btn_wallet')}\n──────────────\n"
        for sym, amt in wallet:
            p = await get_price(sym)
            if p:
                val = p * amt
                total += val
                report += f"💰 {sym}: {amt} (~${val:,.2f})\n"
        report += "──────────────\n"
        report += f"💵 TOTAL: ${total:,.2f}"
        await msg.edit_text(report)

    elif txt in [TEXTS["tr"]["btn_alarm"], TEXTS["en"]["btn_alarm"]]:
        alarms = database.get_alarm_favs(uid)
        await message.answer(f"📡 {t('btn_alarm')}: ON\n📋: {', '.join(alarms) if alarms else '---'}")

# --- 4. AYARLAR ALT MENÜSÜ ---
@dp.callback_query(F.data.startswith("conf_"))
async def conf_handler(call: CallbackQuery):
    uid = call.from_user.id
    mode = call.data.split("_")[1]
    t = lambda k: get_t(uid, k)
    
    if mode == "info":
        await call.message.edit_text(t("info_msg"), reply_markup=settings_kb(uid))
    elif mode == "lang":
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🇹🇷 Türkçe", callback_data="lang_tr"), InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")]])
        await call.message.edit_text(t("select_lang"), reply_markup=kb)
    elif mode in ["market", "alarm", "wallet"]:
        items = []
        if mode == "market": items = database.get_market_favs(uid)
        elif mode == "alarm": items = database.get_alarm_favs(uid)
        elif mode == "wallet": items = [x[0] for x in database.get_wallet(uid)]
        
        text = f"{t('set_' + mode)}\n\n📋: {', '.join(items) if items else '---'}\n\n👇:"
        await call.message.edit_text(text, reply_markup=action_kb(uid, mode))

@dp.callback_query(F.data == "back_settings")
async def back_to_settings(call: CallbackQuery):
    t = lambda k: get_t(call.from_user.id, k)
    USER_STATES[call.from_user.id] = None
    await call.message.edit_text(t("settings_title"), reply_markup=settings_kb(call.from_user.id))

# --- 5. EKLE / ÇIKAR AKSİYONLARI ---
@dp.callback_query(F.data.startswith(("add_", "del_")))
async def action_handler(call: CallbackQuery):
    action, mode = call.data.split("_")
    uid = call.from_user.id
    t = lambda k: get_t(uid, k)
    
    # Hangi işlem yapılıyor kaydet (Add/Del)
    TEMP_DATA[f"{uid}_mode"] = action 

    if mode == "wallet":
        USER_STATES[uid] = "wait_wallet_symbol"
        await call.message.answer(t("enter_symbol"))
    else:
        USER_STATES[uid] = f"wait_{mode}_{action}"
        await call.message.answer(t("enter_symbol"))
    
    await call.answer()

# --- 6. ARKA PLAN TARAYICI ---
async def market_scanner():
    print("👀 Sniper Aktif...")
    while True:
        try:
            unique_coins = database.get_all_unique_alarms()
            if unique_coins:
                for coin in unique_coins:
                    url = "https://api.binance.com/api/v3/klines"
                    params = {"symbol": f"{coin}USDT", "interval": "1m", "limit": 2}
                    async with aiohttp.ClientSession() as s:
                        async with s.get(url, params=params) as r:
                            if r.status == 200:
                                data = await r.json()
                                last = data[-1]
                                open_p = float(last[1])
                                close_p = float(last[4])
                                change = ((close_p - open_p) / open_p) * 100
                                if abs(change) >= 1.0:
                                    users = database.get_users_tracking_coin(coin)
                                    for uid in users:
                                        t = lambda k: get_t(uid, k)
                                        yon = "🚀" if change > 0 else "🔻"
                                        try: await bot.send_message(uid, t("alarm_hit").format(coin, yon, change, close_p))
                                        except: pass
                    await asyncio.sleep(1)
            await asyncio.sleep(60)
        except: await asyncio.sleep(60)

# --- RENDER Fk ---
async def handle(request):
    return web.Response(text="Cryptology Bot is running smoothly! 🚀")

async def main():
    print("🚀 CRYPTOLOGY V7 (Render Port Fix) Started")
    asyncio.create_task(market_scanner())
    
    # Render door
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"🌐 Render Dummy Server Aktif (Port: {port})")

    # Asıl botu başlat
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())