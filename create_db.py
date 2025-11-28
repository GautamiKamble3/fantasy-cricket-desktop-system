import sqlite3

DB_NAME = "fantasy_cricket.db"

conn = sqlite3.connect(DB_NAME)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    team TEXT NOT NULL,
    role TEXT NOT NULL,
    credits INTEGER NOT NULL,
    matches INTEGER DEFAULT 0,
    runs INTEGER DEFAULT 0,
    wickets INTEGER DEFAULT 0
);
""")

players = [
    ("Rohit Sharma","IND","BAT",10,250,10000,0),
    ("Virat Kohli","IND","BAT",11,260,13000,4),
    ("Hardik Pandya","IND","AR",10,120,3000,70),
    ("Jasprit Bumrah","IND","BOWL",11,150,250,250),
    ("KL Rahul","IND","WK",9,120,5000,0)
]

cur.executemany("""
INSERT INTO players(name,team,role,credits,matches,runs,wickets)
VALUES(?,?,?,?,?,?,?)
""", players)

conn.commit()
conn.close()

print("Database created successfully: fantasy_cricket.db")
