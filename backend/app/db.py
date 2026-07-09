"""
db.py
-----
Lớp truy cập SQLite (không dùng ORM nặng - chỉ sqlite3 chuẩn).

Chứa:
    - Khởi tạo schema (bảng users, messages) đúng đặc tả.
    - Các hàm CRUD tối giản phục vụ 6 endpoint.

QUAN TRỌNG: bảng messages CHỈ lưu dữ liệu đã mã hóa
(encrypted_key, iv, ciphertext, auth_tag, signature) + metadata.
KHÔNG bao giờ lưu audio gốc hay AES key thô -> chứng minh encryption-at-rest.
"""

import sqlite3
from pathlib import Path

# File DB: backend/data.db
DB_PATH = Path(__file__).resolve().parent.parent / "data.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    username     TEXT PRIMARY KEY,
    public_key   TEXT NOT NULL,      -- PEM
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    sender         TEXT NOT NULL,
    recipient      TEXT NOT NULL,
    encrypted_key  TEXT NOT NULL,     -- RSA-OAEP(AES key), base64
    iv             TEXT NOT NULL,     -- base64
    ciphertext     TEXT NOT NULL,     -- AES-GCM(audio), base64
    auth_tag       TEXT NOT NULL,     -- base64
    signature      TEXT NOT NULL,     -- RSA-PSS, base64
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sender) REFERENCES users(username),
    FOREIGN KEY (recipient) REFERENCES users(username)
);
"""


def get_conn() -> sqlite3.Connection:
    """Mở kết nối mới, bật row_factory để trả dict-like rows."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    """Tạo bảng nếu chưa tồn tại (gọi lúc khởi động app)."""
    conn = get_conn()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


# ------------------------------- USERS -------------------------------------
def create_user(username: str, public_key_pem: str) -> None:
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO users (username, public_key) VALUES (?, ?)",
            (username, public_key_pem),
        )
        conn.commit()
    finally:
        conn.close()


def get_user(username: str):
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT username, public_key, created_at FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_users() -> list[dict]:
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT username, public_key, created_at FROM users ORDER BY username"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ------------------------------ MESSAGES -----------------------------------
def insert_message(sender: str, recipient: str, payload: dict) -> int:
    """
    Lưu 1 voice message đã mã hóa. `payload` là dict từ crypto.encrypt_message().
    Trả về id tin nhắn vừa tạo.
    """
    conn = get_conn()
    try:
        cur = conn.execute(
            """INSERT INTO messages
               (sender, recipient, encrypted_key, iv, ciphertext, auth_tag, signature)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                sender,
                recipient,
                payload["encrypted_key"],
                payload["iv"],
                payload["ciphertext"],
                payload["auth_tag"],
                payload["signature"],
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_message(message_id: int):
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM messages WHERE id = ?", (message_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_messages_for(recipient: str) -> list[dict]:
    """Danh sách tin nhắn ĐẾN của recipient (mới nhất trước). Vẫn ở dạng mã hóa."""
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM messages WHERE recipient = ? ORDER BY id DESC",
            (recipient,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
