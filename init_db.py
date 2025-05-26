from app import app, db
from app import Schedule, Song
import sqlite3



with app.app_context():
    db.drop_all()
    db.create_all()
    print("Database reset comleted.")