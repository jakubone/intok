import shelve
import os

class DB:
    def __init__(self, db_path):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path

    def set(self, key, value):
        with shelve.open(self.db_path) as db:
            db[key] = value

    def get(self, key):
        with shelve.open(self.db_path) as db:
            return db.get(key, None)

    def delete(self, key):
        with shelve.open(self.db_path) as db:
            if key in db:
                del db[key]

    def list_keys(self):
        with shelve.open(self.db_path) as db:
            return list(db.keys())