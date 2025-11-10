import sqlite3

conn = sqlite3.connect("pricetracker.db")

cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS prices (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               product TEXT NOT NULL,
               company TEXT NOT NULL, 
               url TEXT NOT NULL,
               date DATETIME NOT NULL,
               price FLOAT NOT NULL,
               price_per_oz FLOAT NOT NULL,
               pack_size TEXT NOT NULL
               )
''')

conn.commit()
conn.close()