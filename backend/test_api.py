"""
test_api.py
-----------
Test PHASE 2 - gọi thật vào API đang chạy tại http://localhost:8000
bằng urllib (không cần thư viện ngoài).

Kịch bản:
    - Tạo 2 user alice, bob (sinh khóa RSA).
    - alice gửi 1 "audio" (base64) cho bob.
    - Kiểm tra DB (qua /raw) chỉ chứa ciphertext, KHÔNG có audio gốc.
    - bob giải mã -> khớp audio gốc.
    - Test bảo mật: sửa tin trong DB rồi decrypt -> phải lỗi.
"""

import base64
import json
import os
import sqlite3
import sys
import urllib.error
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE = "http://localhost:8000"
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.db")

passed = failed = 0


def check(name, cond):
    global passed, failed
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
    if cond:
        passed += 1
    else:
        failed += 1


def req(method, path, body=None, expect_error=False):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method,
                               headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def main():
    print("-" * 60)
    print("PHASE 2 - TEST API + DB")
    print("-" * 60)

    # 1. Tạo user
    req("POST", "/users", {"username": "alice"})
    req("POST", "/users", {"username": "bob"})
    status, users = req("GET", "/users")
    names = {u["username"] for u in users}
    check("Tạo & liệt kê user (alice, bob)", {"alice", "bob"} <= names)

    # 2. alice gửi audio cho bob
    fake_audio = os.urandom(2048)
    audio_b64 = base64.b64encode(fake_audio).decode()
    status, sent = req("POST", "/messages",
                       {"sender": "alice", "recipient": "bob",
                        "audio_base64": audio_b64})
    check("POST /messages trả 200", status == 200)
    msg_id = sent["id"]
    check("Response có payload mã hóa (5 trường)",
          set(sent["payload"]) == {"encrypted_key", "iv", "ciphertext",
                                   "auth_tag", "signature"})

    # 3. Kiểm tra DB không lưu audio gốc
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = dict(conn.execute("SELECT * FROM messages WHERE id=?", (msg_id,)).fetchone())
    cols = ",".join(row.keys())
    check("DB KHÔNG có cột audio gốc", "audio" not in cols.lower())
    check("ciphertext trong DB KHÁC audio gốc",
          base64.b64decode(row["ciphertext"]) != fake_audio)
    conn.close()

    # 4. /raw trả bản ghi thô (toàn base64)
    status, raw = req("GET", f"/messages/{msg_id}/raw")
    check("/raw có ciphertext base64, không có audio",
          "ciphertext" in raw and "audio_base64" not in raw)

    # 5. GET danh sách tin của bob (chưa giải mã)
    status, inbox = req("GET", "/messages/bob")
    check("GET /messages/bob liệt kê tin (chưa có audio giải mã)",
          any(m["id"] == msg_id and "audio_base64" not in m for m in inbox))

    # 6. Giải mã hợp lệ
    status, dec = req("POST", f"/messages/{msg_id}/decrypt")
    check("Decrypt trả 200", status == 200)
    check("Audio giải mã KHỚP audio gốc",
          base64.b64decode(dec["audio_base64"]) == fake_audio)

    # 7. Bảo mật: sửa ciphertext trong DB rồi decrypt -> phải lỗi
    conn = sqlite3.connect(DB_PATH)
    ct = conn.execute("SELECT ciphertext FROM messages WHERE id=?",
                      (msg_id,)).fetchone()[0]
    bad = ("A" if ct[0] != "A" else "B") + ct[1:]
    conn.execute("UPDATE messages SET ciphertext=? WHERE id=?", (bad, msg_id))
    conn.commit()
    conn.close()
    status, err = req("POST", f"/messages/{msg_id}/decrypt")
    check("Sửa ciphertext trong DB -> decrypt bị từ chối (400)", status == 400)
    print(f"       thông báo: {err.get('detail')}")

    print("-" * 60)
    print(f"KẾT QUẢ: PASSED {passed} | FAILED {failed}")
    print("-" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
