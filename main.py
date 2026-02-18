import os
import asyncio
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import aiohttp

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