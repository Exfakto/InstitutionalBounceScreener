from pathlib import Path
import sqlite3

from database.schema import PRICE_HISTORY_TABLE

DATABASE_NAME = "InstitutionalBounce.db"
DATABASE_PATH = Path("data") / DATABASE_NAME


class Database:

    def __init__(self):

        DATABASE_PATH.parent.mkdir(exist_ok=True)

        self.connection = sqlite3.connect(DATABASE_PATH)
        self.cursor = self.connection.cursor()

    def initialize(self):

        self.cursor.execute(PRICE_HISTORY_TABLE)

        self.connection.commit()

    def close(self):

        self.connection.close()