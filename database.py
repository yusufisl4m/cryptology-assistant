import sqlite3

# Veritabanı dosyasının adı
DB_NAME = "crypto_wallet.db"

def init_db():
    """Veritabanını ve tabloyu oluşturur (Eğer yoksa)"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Cüzdan Tablosu: Kullanıcı ID, Coin İsmi, Miktar
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wallet (
            user_id INTEGER,
            symbol TEXT,
            amount REAL,
            PRIMARY KEY (user_id, symbol)
        )
    ''')
    conn.commit()
    conn.close()

def add_coin(user_id, symbol, amount):
    """Cüzdana coin ekler veya varsa günceller"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Önce var mı diye bak, varsa üzerine ekle (Upsert mantığı)
    cursor.execute("INSERT OR REPLACE INTO wallet (user_id, symbol, amount) VALUES (?, ?, ?)", 
                   (user_id, symbol.upper(), amount))
    
    conn.commit()
    conn.close()

def get_wallet(user_id):
    """Kullanıcının tüm coinlerini getirir"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT symbol, amount FROM wallet WHERE user_id = ?", (user_id,))
    data = cursor.fetchall()
    conn.close()
    return data # Örn: [('BTC', 0.5), ('ETH', 2.0)]

def delete_coin(user_id, symbol):
    """Cüzdandan coin siler"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM wallet WHERE user_id = ? AND symbol = ?", (user_id, symbol.upper()))
    conn.commit()
    conn.close()