import os
import asyncio
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import aiohttp
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# Veritabanı modülümüzü çağırıyoruz
import database

# 1. Ayarları Yükle
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

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
# --- BUTON TIKLAMA İŞLEYİCİSİ (GELİŞMİŞ) ---
@dp.callback_query()
async def menu_handler(callback: CallbackQuery):
    action = callback.data
    
    # Geri Dönme Butonu (Her ekranın altına koyacağız)
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

        # Hesaplama yapılıyor efekti
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
        
        # Mesajı güncelle
        await callback.message.edit_text(report, reply_markup=btn_back)

    # 2. 📈 PİYASALAR BUTONU
    elif action == "menu_piyasa":
        await callback.answer("Veriler çekiliyor...")
        
        # Örnek olarak 3 büyük coini çekelim
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

    # 3. 🔙 ANA MENÜYE DÖNÜŞ
    elif action == "main_menu":
        # /start komutundaki menüyü tekrar çağır
        await cmd_start(callback.message)

    # 4. DİĞERLERİ
    else:
        await callback.answer("🚧 Bu özellik (Alarm/Ayarlar) yakında eklenecek!", show_alert=True)

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

# --- ANA ÇALIŞTIRMA ---
async def main():
    print("🚀 Cryptology (V2 - Cüzdan Modu) Aktif")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())