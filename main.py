import os
import asyncio
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import aiohttp
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# Veritabanı modülü çağırma
import database

# 1. Ayarları Yükle
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# --- SNIPER AYARLARI ---
WATCHLIST = ["BTC", "ETH", "SOL", "XRP", "BNB", "DOGE", "ADA", "AVAX"]
ALERT_THRESHOLD = 1.0  # %1 ve üzeri değişimde haber ver
VOLUME_MULTIPLIER = 5.0  # Ortalama hacmin 5 katına çıkarsa haber ver
ALARM_STATUS = True  # Başlangıçta alarmlar açık

# 2. Loglama
logging.basicConfig(level=logging.INFO)

# 3. Bot Kurulumu
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Veritabanını başlat (Dosya yoksa oluşturur)
database.init_db()

# --- BİNANCE API ---
async def get_binance_price(symbol):
    url = "https://api.binance.com/api/v3/ticker/price"
    params = {"symbol": f"{symbol.upper()}USDT"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return float(data['price'])
            return 0.0
# --- KOMUT: BAŞLANGIÇ (/start) ---
@dp.message(Command("start"))
# --- KOMUT: BAŞLANGIÇ (/start) ---
@dp.message(Command("start"))
async def cmd_start(message: Message):
    # 1. Butonları Tanımla
    btn_piyasa = InlineKeyboardButton(text="📈 Piyasalar", callback_data="menu_piyasa")
    btn_cuzdan = InlineKeyboardButton(text="👛 Cüzdanım", callback_data="menu_cuzdan")
    btn_alarm  = InlineKeyboardButton(text="🚨 Alarmlar", callback_data="menu_alarm")
    btn_ayar   = InlineKeyboardButton(text="⚙️ Ayarlar", callback_data="menu_ayar")

    # 2. Düzeni Oluştur (Satır Satır)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [btn_piyasa, btn_cuzdan],  # İlk satır
        [btn_alarm, btn_ayar]      # İkinci satır
    ])

    # 3. Mesajı Gönder
    await message.answer(
        "👋**Merhaba Ben Cryptology! **⚡\n\n"
        "Yatırımlarını yönetmek için aşağıdaki menüyü kullanabilirsin. "
        "Anlık takipler ve analizler parmaklarının ucunda! 🚀",
        reply_markup=keyboard
    )
# --- BUTON TIKLAMA İŞLEYİCİSİ---
@dp.callback_query()
async def menu_handler(callback: CallbackQuery):
    action = callback.data
    
    # Geri Dönme Butonu (Her ekranın altına koy)
    btn_back = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Ana Menü", callback_data="main_menu")]
    ])

    # 1. 👛 CÜZDANIM BUTONU
    if action == "menu_cuzdan":
        user_id = callback.from_user.id
        coins = database.get_wallet(user_id)

        if not coins:
            text = "📭 Cüzdanın boş! /ekle BTC 0.5 yazarak coin ekleyebilirsin."
            await callback.message.edit_text(text, reply_markup=btn_back)
            return

        await callback.answer("Hesaplanıyor...") 
        
        total_value = 0.0
        report = "💼 **PORTFÖYÜN**\n──────────────\n"

        for symbol, amount in coins:
            price = await get_binance_price(symbol)
            if price > 0:
                value = price * amount
                total_value += value
                report += f"🔹 {symbol}: {amount} adet (~${value:,.2f})\n"
            else:
                report += f"⚠️ {symbol}: Fiyat alınamadı\n"

        report += "──────────────\n"
        report += f"💰 TOPLAM: ${total_value:,.2f}"
        
        await callback.message.edit_text(report, reply_markup=btn_back)

    # 2. 📈 PİYASALAR BUTONU
    elif action == "menu_piyasa":
        await callback.answer("Veriler çekiliyor...")
        
        # Örnek 3 büyük coin
        btc = await get_binance_price("BTC")
        eth = await get_binance_price("ETH")
        bnb = await get_binance_price("BNB")
        
        market_text = (
            "📊 **PİYASA ÖZETİ**\n"
            "──────────────\n"
            f"👑 BTC: ${btc:,.2f}\n"
            f"💎 ETH: ${eth:,.2f}\n"
            f"🔶 BNB: ${bnb:,.2f}\n"
            "──────────────\n"
            "💡 *Daha fazlası için: /btc gibi komutlar kullanabilirsin.*"
        )
        await callback.message.edit_text(market_text, reply_markup=btn_back)

    # 3. ALARMLAR BUTONU 
    elif action == "menu_alarm":
        global ALARM_STATUS
        # Durumu tersine çevir (Açıksa kapat, kapalıysa aç)
        ALARM_STATUS = not ALARM_STATUS
        
        status_text = "🟢 AKTİF" if ALARM_STATUS else "🔴 KAPALI"
        msg = (
            f"📡 **SNIPER ALARM SİSTEMİ**\n"
            f"──────────────\n"
            f"Durum: **{status_text}**\n\n"
            f"🔍 Takip Edilenler: {', '.join(WATCHLIST)}\n"
            f"⚡ Fiyat Hassasiyeti: %{ALERT_THRESHOLD}\n"
            f"🐋 Hacim Hassasiyeti: {VOLUME_MULTIPLIER}x Kat"
        )
        await callback.message.edit_text(msg, reply_markup=btn_back)

    # 4. 🔙 ANA MENÜYE DÖNÜŞ
    elif action == "main_menu":
        await cmd_start(callback.message)
    
    # 5. AYARLAR (Henüz boş)
    else:
        await callback.answer("🚧 Ayarlar menüsü yakında!", show_alert=True)

# --- KOMUT: COİN EKLEME (/ekle BTC 0.5) ---
@dp.message(Command("ekle"))
async def cmd_add_coin(message: types.Message):
    try:
        # Mesajı parçala: "/ekle", "BTC", "0.5"
        parts = message.text.split()
        if len(parts) != 3:
            await message.answer("⚠️ Kullanım: `/ekle [COIN] [MIKTAR]`\nÖrnek: `/ekle BTC 0.5`")
            return

        symbol = parts[1].upper()
        amount = float(parts[2])

        # Veritabanına kaydet
        database.add_coin(message.from_user.id, symbol, amount)
        await message.answer(f"✅ {symbol} Cüzdanınıza eklendi.\nMiktar: {amount}")

    except ValueError:
        await message.answer("❌ Lütfen geçerli bir sayı girin.")

# --- KOMUT: CÜZDAN SİLME (/sil BTC) ---
@dp.message(Command("sil"))
async def cmd_del_coin(message: types.Message):
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("⚠️ Kullanım: `/sil [COIN]`\nÖrnek: `/sil BTC`")
        return
    
    symbol = parts[1].upper()
    database.delete_coin(message.from_user.id, symbol)
    await message.answer(f"🗑️ {symbol} cüzdanınızdan silindi.")

# --- KOMUT: CÜZDAN DURUMU (/cuzdan) ---
@dp.message(Command("cuzdan"))
async def cmd_show_wallet(message: types.Message):
    user_id = message.from_user.id
    coins = database.get_wallet(user_id) # Veritabanından çek

    if not coins:
        await message.answer("📭 Cüzdanınız boş. /ekle komutu ile coin ekleyin.")
        return

    msg = await message.answer("🔄 Cüzdan Verileri Hesaplanıyor...")
    
    total_value = 0.0
    report = "💼 **PORTFÖY RAPORU**\n──────────────\n"

    for symbol, amount in coins:
        price = await get_binance_price(symbol)
        if price > 0:
            value = price * amount
            total_value += value
            report += f"🔹 {symbol}: {amount} adet (~${value:,.2f})\n"
        else:
            report += f"⚠️ {symbol}: Fiyat alınamadı\n"

    report += "──────────────\n"
    report += f"💰 TOPLAM VARLIK: ${total_value:,.2f}"

    await msg.edit_text(report)

    # --- ARKA PLAN: PİYASA TARAYICISI ---
async def market_scanner():
    print("👀 Sniper Modu Başladı: Piyasalar taranıyor...")
    
    while True:
        if ALARM_STATUS:
            for coin in WATCHLIST:
                try:
                    # Binance'den son 15 dakikalık mum verilerini çek
                    url = "https://api.binance.com/api/v3/klines"
                    params = {
                        "symbol": f"{coin}USDT",
                        "interval": "1m",  # 1 dakikalık mumlar
                        "limit": 15        # Son 15 mum
                    }
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, params=params) as response:
                            if response.status == 200:
                                data = await response.json()
                                # Veri Formatı: [Zaman, Açılış, Yüksek, Düşük, Kapanış, Hacim, ...]
                                
                                # Son kapanan mum (Tamamlanmış veri için sondan bir öncekine bak)
                                last_candle = data[-2]
                                open_price = float(last_candle[1])
                                close_price = float(last_candle[4])
                                current_volume = float(last_candle[5])
                                
                                # 1. FİYAT ALARMI HESAPLAMA
                                change_percent = ((close_price - open_price) / open_price) * 100
                                
                                # 2. HACİM ALARMI HESAPLAMA
                                # Önceki 14 mumun hacim ortalamasını al
                                previous_volumes = [float(candle[5]) for candle in data[:-2]]
                                avg_volume = sum(previous_volumes) / len(previous_volumes) if previous_volumes else 1
                                
                                # --- KONTROL MEKANİZMASI ---
                                
                                # Senaryo A: Ani Fiyat Hareketi
                                if abs(change_percent) >= ALERT_THRESHOLD:
                                    direction = "🚀 FIRLADI" if change_percent > 0 else "🔻 ÇAKILDI"
                                    # Yöneticinin ID'sini .env dosyasından alıp mesaj salla
                                    admin_id = os.getenv("ADMIN_ID") 
                                    if admin_id:
                                        await bot.send_message(
                                            admin_id,
                                            f"🚨 **PİYASA ALARMI: {coin}**\n"
                                            f"──────────────\n"
                                            f"{direction}: **%{change_percent:.2f}**\n"
                                            f"💵 Fiyat: ${close_price}\n"
                                            f"⏱️ Süre: Son 1 Dakika"
                                        )

                                # Senaryo B: Balina Hacmi (Whale Alert)
                                elif current_volume > (avg_volume * VOLUME_MULTIPLIER):
                                    admin_id = os.getenv("ADMIN_ID")
                                    if admin_id:
                                        await bot.send_message(
                                            admin_id,
                                            f"🐋 **BALİNA ALARMI: {coin}**\n"
                                            f"──────────────\n"
                                            f"📊 Hacim Patlaması: **{VOLUME_MULTIPLIER}x Kat**\n"
                                            f"💵 Anlık Fiyat: ${close_price}"
                                        )
                                        
                except Exception as e:
                    print(f"Hata ({coin}): {e}")
                
                # Her coin arasında 1 saniye bekle (Binance banlama)
                await asyncio.sleep(1)# Tüm listeyi taradıktan sonra 60 saniye dinlen
        await asyncio.sleep(60)

# --- ANA ÇALIŞTIRMA ---
async def main():
    print("🚀 Cryptology (V3 - Snip Modu) Aktif")
    await dp.start_polling(bot)
    asyncio.create_task(market_scanner())
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())