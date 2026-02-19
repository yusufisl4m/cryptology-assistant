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
        "👋 **Merhaba Cryptology!**\n\n"
        "Yatırımlarını yönetmek için aşağıdaki menüyü kullanabilirsin. "
        "Anlık takipler ve analizler parmaklarının ucunda! 🚀",
        reply_markup=keyboard
    )
# --- BUTON TIKLAMA İŞLEYİCİSİ ---
@dp.callback_query()
async def menu_handler(callback: CallbackQuery):
    action = callback.data # Tıklanan butonun kimliği (örn: menu_cuzdan)

    if action == "menu_cuzdan":
        # Eğer Cüzdanım'a bastıysa cüzdan komutunu çalıştır (İleride bağlayacağız)
        await callback.answer("👛 Cüzdan moduna geçiliyor...")
        await callback.message.answer("Cüzdanın için: /cuzdan komutunu kullanabilirsin!")
        
    elif action == "menu_piyasa":
        await callback.answer("📈 Piyasa verileri yükleniyor...")
        await callback.message.answer("Hangi coine bakmak istersin? Örn: `/btc`")
        
    else:
        # Diğer butonlar (Alarm, Ayarlar) için şimdilik boş dön
        await callback.answer("🚧 Bu özellik geliştirme aşamasında!", show_alert=True)
        
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