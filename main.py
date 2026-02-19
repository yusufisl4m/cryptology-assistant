import os
import asyncio
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import aiohttp
import database

# 1. AYARLAR
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# Geçici Kullanıcı Durumları (RAM'de tutulur)
# Örn: {12345: "waiting_wallet_add_symbol"}
USER_STATES = {}
TEMP_DATA = {} # Ara verileri tutmak için (örn: eklenecek coin sembolü)

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
        "enter_amount": "✍️ Lütfen miktarı yazın (Örn: 0.5):",
        "success_add": "✅ {} başarıyla eklendi!",
        "success_del": "🗑️ {} silindi!",
        "info_msg": (
            "ℹ️ **CRYPTOLOGY ASİSTAN BİLGİSİ**\n\n"
            "🤖 **Nedir?**\nSizin için kripto paraları takip eden, cüzdanınızı hesaplayan ve ani hareketleri bildiren akıllı bir asistandır.\n\n"
            "🎛 **Nasıl Kullanılır?**\n"
            "• Piyasalar: Favori coinlerinizin anlık durumunu ve Korku/Açgözlülük endeksini gösterir.\n"
            "• Cüzdanım: Sahip olduğunuz varlıkların toplam değerini hesaplar.\n"
            "• Alarmlar: Seçtiğiniz coinlerde %1'lik ani hareket veya 5x hacim girişi olursa size haber verir.\n"
            "• Ayarlar: Tüm bu listeleri özelleştirebileceğiniz kontrol merkezidir."
        ),
        "fng_title": "🧠 **PİYASA RUH HALİ**",
        "alarm_hit": "🚨 **ALARM: {}**\n{} %{:.2f}\n💰 Fiyat: ${}"
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
        "enter_amount": "✍️ Please type amount (e.g. 0.5):",
        "success_add": "✅ {} added successfully!",
        "success_del": "🗑️ {} deleted!",
        "info_msg": (
            "ℹ️ **CRYPTOLOGY INFO**\n\n"
            "🤖 **What is this?**\nA smart assistant that tracks crypto, calculates your portfolio, and notifies you of pumps/dumps.\n\n"
            "🎛 **How to use?**\n"
            "• Markets: Shows live prices of your favorites & Fear/Greed index.\n"
            "• Wallet: Calculates total value of your assets.\n"
            "• Alarms: Notifies you on %1 price moves or 5x volume spikes.\n"
            "• Settings: The control center to customize all lists."
        ),
        "fng_title": "🧠 **MARKET SENTIMENT**",
        "alarm_hit": "🚨 **ALERT: {}**\n{} %{:.2f}\n💰 Price: ${}"
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

# --- 1. BAŞLANGIÇ (/start) ---
@dp.message(Command("start"))
async def cmd_start(message: Message):
    # Önce Bot İsmi
    await message.answer(TEXTS["tr"]["welcome_title"])
    
    # Sonra Dil Seçimi
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

# --- 3. ANA MENÜ BUTONLARI (Reply Keyboard) ---
@dp.message(F.text)
async def reply_handler(message: Message):
    uid = message.from_user.id
    txt = message.text
    t = lambda k: get_t(uid, k)

    # Durum kontrolü (Veri girişi mi yapılıyor?)
    state = USER_STATES.get(uid)
    
    if state:
        # --- VERİ GİRİŞİ İŞLEME ---
        if txt.startswith("/"): return # Komutsa iptal et
        
        if state == "wait_market_add":
            database.add_market_fav(uid, txt)
            await message.answer(t("success_add").format(txt.upper()))
        
        elif state == "wait_market_del":
            database.del_market_fav(uid, txt)
            await message.answer(t("success_del").format(txt.upper()))

        elif state == "wait_alarm_add":
            database.add_alarm_fav(uid, txt)
            await message.answer(t("success_add").format(txt.upper()))
            
        elif state == "wait_alarm_del":
            database.del_alarm_fav(uid, txt)
            await message.answer(t("success_del").format(txt.upper()))
            
        elif state == "wait_wallet_symbol":
            TEMP_DATA[uid] = txt
            USER_STATES[uid] = "wait_wallet_amount"
            await message.answer(t("enter_amount"))
            return # Miktar bekle
            
        elif state == "wait_wallet_amount":
            try:
                amt = float(txt)
                sym = TEMP_DATA.get(uid)
                database.update_wallet(uid, sym, amt)
                await message.answer(t("success_add").format(f"{amt} {sym.upper()}"))
            except:
                await message.answer("❌ Number only!")

        # İşlem bitince durumu sıfırla
        USER_STATES[uid] = None
        return

    # --- NORMAL MENÜ İŞLEMLERİ ---
    
    # AYARLAR (SETTINGS) - ÖZEL MENÜ AÇAR
    if txt in [TEXTS["tr"]["btn_settings"], TEXTS["en"]["btn_settings"]]:
        await message.answer(t("settings_title"), reply_markup=settings_kb(uid))

    # PİYASALAR (MARKETS)
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
        
        # Korku Endeksi
        fng = await get_fng()
        if fng:
            report += f"\n{t('fng_title')}: {fng['value']} ({fng['value_classification']})"
            
        await msg.edit_text(report)

    # CÜZDANIM (WALLET)
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

    # ALARMLAR (ALARMS)
    elif txt in [TEXTS["tr"]["btn_alarm"], TEXTS["en"]["btn_alarm"]]:
        # Sadece listeyi gösterir, düzenleme Ayarlar'da
        alarms = database.get_alarm_favs(uid)
        status = "🟢 ON" # Tarayıcı hep çalışır
        await message.answer(f"📡 {t('btn_alarm')}: {status}\n📋: {', '.join(alarms) if alarms else '---'}")

# --- 4. AYARLAR ALT MENÜSÜ (INLINE) ---
@dp.callback_query(F.data.startswith("conf_"))
async def conf_handler(call: CallbackQuery):
    uid = call.from_user.id
    mode = call.data.split("_")[1]
    t = lambda k: get_t(uid, k)
    
    if mode == "info":
        await call.message.edit_text(t("info_msg"), reply_markup=settings_kb(uid))
        
    elif mode == "lang":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🇹🇷 Türkçe", callback_data="lang_tr"),
             InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")]
        ])
        await call.message.edit_text(t("select_lang"), reply_markup=kb)
        
    elif mode in ["market", "alarm", "wallet"]:
        # Listeyi göster ve Ekle/Çıkar butonlarını sun
        title = {"market": "set_market", "alarm": "set_alarm", "wallet": "set_wallet"}[mode]
        
        # Mevcut listeyi çek
        if mode == "market": items = database.get_market_favs(uid)
        elif mode == "alarm": items = database.get_alarm_favs(uid)
        elif mode == "wallet": items = [x[0] for x in database.get_wallet(uid)]
        
        list_str = ", ".join(items) if items else "---"
        text = f"{t(title)}\n\n📋: {list_str}\n\n👇:"
        await call.message.edit_text(text, reply_markup=action_kb(uid, mode))

@dp.callback_query(F.data == "back_settings")
async def back_to_settings(call: CallbackQuery):
    t = lambda k: get_t(call.from_user.id, k)
    USER_STATES[call.from_user.id] = None # Durumu sıfırla
    await call.message.edit_text(t("settings_title"), reply_markup=settings_kb(call.from_user.id))

# --- 5. EKLE / ÇIKAR AKSİYONLARI ---
@dp.callback_query(F.data.startswith(("add_", "del_")))
async def action_handler(call: CallbackQuery):
    action, mode = call.data.split("_")
    uid = call.from_user.id
    t = lambda k: get_t(uid, k)
    
    # Kullanıcıyı "yazma" moduna al
    if mode == "wallet" and action == "add":
        USER_STATES[uid] = "wait_wallet_symbol"
        await call.message.answer(t("enter_symbol"))
    elif mode == "wallet" and action == "del":
        # Cüzdandan silmek için sembol sor (miktar 0 yapılacak)
        USER_STATES[uid] = "wait_wallet_symbol" 
        # (Mantık: Miktarı 0 girerse silinir fonksiyonu kullanacağız ama basit olsun diye direkt isim soralım)
        # Basitleştirme: Silme de aynı mantık, kullanıcı adını yazsın.
        USER_STATES[uid] = "wait_wallet_symbol" # Burası geliştirilebilir, şimdilik ekleme mantığıyla gidiyoruz
        await call.message.answer("🗑️ Silinecek coin sembolünü yazın:")
        # Not: update_wallet fonksiyonu 0 gönderirse siliyor, ikinci adımda 0 isteyeceğiz.
        
    else:
        # Market veya Alarm
        USER_STATES[uid] = f"wait_{mode}_{action}"
        await call.message.answer(t("enter_symbol"))
        
    await call.answer()

# --- 6. ARKA PLAN TARAYICI (GLOBAL & KİŞİSELLEŞTİRİLMİŞ) ---
async def market_scanner():
    print("👀 Sniper Aktif...")
    while True:
        try:
            # 1. Tüm benzersiz takip edilen coinleri bul
            unique_coins = database.get_all_unique_alarms()
            
            if unique_coins:
                for coin in unique_coins:
                    # Binance verisi çek
                    url = "https://api.binance.com/api/v3/klines"
                    params = {"symbol": f"{coin}USDT", "interval": "1m", "limit": 2}
                    async with aiohttp.ClientSession() as s:
                        async with s.get(url, params=params) as r:
                            if r.status == 200:
                                data = await r.json()
                                last = data[-1] # Henüz kapanmamış mum anlık takip için
                                open_p = float(last[1])
                                close_p = float(last[4])
                                change = ((close_p - open_p) / open_p) * 100
                                
                                # Hareket varsa (%1)
                                if abs(change) >= 1.0:
                                    # Bu coini takip edenleri bul
                                    users = database.get_users_tracking_coin(coin)
                                    for uid in users:
                                        t = lambda k: get_t(uid, k)
                                        yon = "🚀" if change > 0 else "🔻"
                                        try:
                                            await bot.send_message(uid, t("alarm_hit").format(coin, yon, change, close_p))
                                        except: pass
                    await asyncio.sleep(1) # API limit
            await asyncio.sleep(60)
        except Exception as e:
            print(f"Sniper Error: {e}")
            await asyncio.sleep(60)

async def main():
    print("🚀 CRYPTOLOGY SYSTEM STARTED")
    asyncio.create_task(market_scanner())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())