import os
import asyncio
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import aiohttp

# 1. Ayarları Yükle (.env dosyasından)
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# 2. Loglama (Hata takibi için)
logging.basicConfig(level=logging.INFO)

# 3. Botu Başlat
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- BİNANCE API MOTORU (Hızın Kaynağı) ---
async def get_binance_price(symbol):
    base_url = "https://api.binance.com/api/v3/ticker/price"
    params = {"symbol": f"{symbol.upper()}USDT"} # BTC -> BTCUSDT
    
    async with aiohttp.ClientSession() as session:
        async with session.get(base_url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return float(data['price'])
            return None

# --- KOMUT: Fiyat Sorgulama (/btc, /eth vb.) ---
@dp.message()
async def handle_crypto_price(message: types.Message):
    # Kullanıcı "/" ile başlayan bir şey yazdı mı? (Örn: /btc)
    if message.text.startswith("/") and len(message.text) > 1:
        coin = message.text[1:] # "/" işaretini at, "btc"yi al
        
        # Kullanıcıya "Bakıyorum..." mesajı ver (Hız hissi için)
        waiting_msg = await message.answer(f"🔍 {coin.upper()} fiyatı çekiliyor...")
        
        price = await get_binance_price(coin)
        
        if price:
            # Fiyatı güzel formatla (Virgülden sonra 2 hane)
            await waiting_msg.edit_text(
                f"💰 **{coin.upper()} / USDT**\n"
                f"──────────────\n"
                f"💵 Fiyat: **${price:,.2f}**"
            )
        else:
            await waiting_msg.edit_text(f"❌ '{coin.upper()}' Binance'de bulunamadı.")

# --- ANA DÖNGÜ ---
async def main():
    print("🚀 Crypto Hunter (V1) Sahneye Çıktı!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())