import sqlite3

DB_NAME = "crypto_wallet.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Cüzdan Tablosu
    cursor.execute('''CREATE TABLE IF NOT EXISTS wallet (
            user_id INTEGER, symbol TEXT, amount REAL,
            PRIMARY KEY (user_id, symbol))''')
    
    # 2. Ayarlar (Dil) Tablosu
    cursor.execute('''CREATE TABLE IF NOT EXISTS settings (
            user_id INTEGER PRIMARY KEY, language TEXT DEFAULT 'tr')''')

    # 3. YENİ: Favori Piyasalar (Markets)
    cursor.execute('''CREATE TABLE IF NOT EXISTS market_favs (
            user_id INTEGER, symbol TEXT,
            PRIMARY KEY (user_id, symbol))''')

    # 4. YENİ: Alarm Listesi (Alerts)
    cursor.execute('''CREATE TABLE IF NOT EXISTS alarm_list (
            user_id INTEGER, symbol TEXT,
            PRIMARY KEY (user_id, symbol))''')
    
    conn.commit()
    conn.close()

# --- TEMEL FONKSİYONLAR ---
def set_language(user_id, lang):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("INSERT OR REPLACE INTO settings (user_id, language) VALUES (?, ?)", (user_id, lang))

def get_language(user_id):
    with sqlite3.connect(DB_NAME) as conn:
        res = conn.execute("SELECT language FROM settings WHERE user_id = ?", (user_id,)).fetchone()
    return res[0] if res else None

# --- CÜZDAN ---
def update_wallet(user_id, symbol, amount):
    with sqlite3.connect(DB_NAME) as conn:
        if amount <= 0:
            conn.execute("DELETE FROM wallet WHERE user_id = ? AND symbol = ?", (user_id, symbol.upper()))
        else:
            conn.execute("INSERT OR REPLACE INTO wallet VALUES (?, ?, ?)", (user_id, symbol.upper(), amount))

def get_wallet(user_id):
    with sqlite3.connect(DB_NAME) as conn:
        return conn.execute("SELECT symbol, amount FROM wallet WHERE user_id = ?", (user_id,)).fetchall()

# --- FAVORİ PİYASALAR (MARKETS) ---
def add_market_fav(user_id, symbol):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("INSERT OR IGNORE INTO market_favs VALUES (?, ?)", (user_id, symbol.upper()))

def del_market_fav(user_id, symbol):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("DELETE FROM market_favs WHERE user_id = ? AND symbol = ?", (user_id, symbol.upper()))

def get_market_favs(user_id):
    with sqlite3.connect(DB_NAME) as conn:
        res = conn.execute("SELECT symbol FROM market_favs WHERE user_id = ?", (user_id,)).fetchall()
    return [r[0] for r in res]

# --- ALARM LİSTESİ ---
def add_alarm_fav(user_id, symbol):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("INSERT OR IGNORE INTO alarm_list VALUES (?, ?)", (user_id, symbol.upper()))

def del_alarm_fav(user_id, symbol):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("DELETE FROM alarm_list WHERE user_id = ? AND symbol = ?", (user_id, symbol.upper()))

def get_alarm_favs(user_id):
    with sqlite3.connect(DB_NAME) as conn:
        res = conn.execute("SELECT symbol FROM alarm_list WHERE user_id = ?", (user_id,)).fetchall()
    return [r[0] for r in res]

# --- GLOBAL ALARMLAR (Tarayıcı İçin) ---
def get_all_unique_alarms():
    """Hangi coinlerin takip edildiğini (tekil olarak) getirir"""
    with sqlite3.connect(DB_NAME) as conn:
        res = conn.execute("SELECT DISTINCT symbol FROM alarm_list").fetchall()
    return [r[0] for r in res]

def get_users_tracking_coin(symbol):
    """Bir coini takip eden kullanıcıların ID'lerini getirir"""
    with sqlite3.connect(DB_NAME) as conn:
        res = conn.execute("SELECT user_id FROM alarm_list WHERE symbol = ?", (symbol,)).fetchall()
    return [r[0] for r in res]
# --- MEVCUT BAKİYE SORGULAMA ---
def get_single_coin_amount(user_id, symbol):
    """Kullanıcının cüzdanındaki belirli bir coinin miktarını getirir"""
    with sqlite3.connect(DB_NAME) as conn:
        res = conn.execute("SELECT amount FROM wallet WHERE user_id = ? AND symbol = ?", (user_id, symbol.upper())).fetchone()
    return res[0] if res else 0.0