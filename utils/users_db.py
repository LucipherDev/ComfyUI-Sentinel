import bcrypt
import json
import os
import hashlib
from pathlib import Path


class UsersDB:
    def __init__(self, database: str | Path):
        self.database = database

        self.users = {}
        self.first_user = (None, {})

        self._database_hash = None

        self.load_users()

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def calculate_file_hash(self) -> str:
        """Calculate the SHA256 hash of the database file."""
        if os.path.exists(self.database):
            with open(self.database, "rb") as f:
                file_data = f.read()
                return hashlib.sha256(file_data).hexdigest()
        return ""

    def load_users(self) -> dict:
        """Load users from the database if it has changed."""
        current_hash = self.calculate_file_hash()
        if current_hash != self._database_hash:
            if os.path.exists(self.database):
                with open(self.database, "r") as f:
                    try:
                        self.users = json.load(f)
                        self._database_hash = current_hash
                    except json.JSONDecodeError:
                        self.users = {}
        return self.users

    def save_users(self, users: dict) -> None:
        """Save users to the database and update the hash."""
        with open(self.database, "w") as f:
            json.dump(users, f)

        self._database_hash = self.calculate_file_hash()

    def add_user(self, id: str, username: str, password: str, admin: bool) -> None:
        """Add a user to the database."""
        self.load_users()
        user = {"username": username, "password": self.hash_password(password)}
        if admin:
            user["admin"] = admin
        self.users[id] = user
        self.save_users(self.users)

    def get_user(self, username: str = "", user_id: str = "") -> tuple[str, dict]:
        """Retrieve a user by username."""
        self.load_users()

        if user_id:
            return user_id, self.users[user_id] or None, {}

        for uid, user_data in self.users.items():
            if user_data["username"] == username:
                return uid, user_data

        return None, {}

    def check_username_password(self, username: str, password: str) -> bool:
        """Check if the username and password match."""
        user_id, user_data = self.get_user(username)
        if not user_id:
            return False

        return bcrypt.checkpw(
            password.encode("utf-8"), user_data["password"].encode("utf-8")
        )

    def get_first_user(self) -> tuple[str, dict] | None:
        """Get the first user from the database."""
        self.load_users()
        for uid, user_data in self.users.items():
            if user_data.get("admin"):
                self.first_user = (uid, user_data)

        return self.first_user
