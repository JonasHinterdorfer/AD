#!/usr/bin/env python3
import sqlite3, os
DB = os.getenv('DB', '/app/data/cryze.db')
con = sqlite3.connect(DB)
cur = con.cursor()
for row in cur.execute('SELECT username,password FROM users'):
    print(row[0], row[1])
