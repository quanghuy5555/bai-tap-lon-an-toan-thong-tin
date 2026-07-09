"""
test_crypto.py
--------------
Script test ĐỘC LẬP cho tầng crypto (PHASE 1). Chạy trực tiếp:

    cd backend
    python test_crypto.py

Kịch bản:
    1. Sinh cặp khóa RSA cho 2 user: alice (gửi) và bob (nhận).
    2. Tạo "audio" giả (bytes ngẫu nhiên) đại diện voice message.
    3. Mã hóa + ký (alice -> bob), in ra ciphertext để thấy nó là RÁC base64.
    4. Giải mã hợp lệ -> so khớp byte-for-byte với audio gốc.
    5. Các test bảo mật (fail-closed):
        - Sửa 1 ký tự ciphertext  -> phải bị TamperError (GCM tag fail).
        - Đổi chữ ký              -> phải bị SignatureError.
        - Sai người nhận (khóa)   -> phải bị lỗi (không giải mã được).

Không phụ thuộc FastAPI/DB - chỉ dùng crypto.py + keystore.py.
"""

import os
import sys

# Ép stdout sang UTF-8 để in được tiếng Việt trên console Windows (cp1252).
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Cho phép chạy "python test_crypto.py" từ thư mục backend/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import crypto, keystore  # noqa: E402


def line(title=""):
    print("-" * 60)
    if title:
        print(title)


def main():
    passed = 0
    failed = 0

    def check(name, condition):
        nonlocal passed, failed
        if condition:
            print(f"  [PASS] {name}")
            passed += 1
        else:
            print(f"  [FAIL] {name}")
            failed += 1

    line("PHASE 1 - TEST CRYPTO CORE (AES-256-GCM + RSA-2048)")

    # 1. Sinh khóa cho 2 user
    keystore.generate_keypair("alice")
    keystore.generate_keypair("bob")
    keystore.generate_keypair("eve")  # kẻ thứ 3 để test sai người nhận

    alice_priv = keystore.load_private_key("alice")     # người gửi
    bob_pub = keystore.public_key_from_pem(keystore.load_public_key_pem("bob"))
    bob_priv = keystore.load_private_key("bob")          # người nhận
    alice_pub = keystore.public_key_from_pem(keystore.load_public_key_pem("alice"))
    eve_priv = keystore.load_private_key("eve")

    # 2. "Audio" giả: 4KB bytes ngẫu nhiên
    fake_audio = os.urandom(4096)
    print(f"\nAudio gốc (giả): {len(fake_audio)} bytes, 16 byte đầu (hex): "
          f"{fake_audio[:16].hex()}")

    # 3. Mã hóa + ký: alice -> bob
    record = crypto.encrypt_message(fake_audio, bob_pub, alice_priv)

    line("Server LƯU gì trong DB (base64, đã rút gọn):")
    for k, v in record.items():
        shown = v if len(v) <= 72 else v[:72] + "..."
        print(f"  {k:14}: {shown}")
    print("  => KHÔNG có audio gốc, chỉ toàn ciphertext base64 vô nghĩa.")

    # 4. Giải mã hợp lệ -> round-trip
    line("Test 1: Round-trip mã hóa -> giải mã hợp lệ")
    recovered = crypto.decrypt_message(record, bob_priv, alice_pub)
    check("Giải mã ra ĐÚNG audio gốc (byte-for-byte)", recovered == fake_audio)
    check("Ciphertext KHÁC audio gốc (đã thực sự mã hóa)",
          crypto._b64d(record["ciphertext"]) != fake_audio)

    # 5a. Tamper ciphertext -> GCM tag fail
    line("Test 2: Sửa ciphertext -> phải bị từ chối (TamperError)")
    tampered = dict(record)
    ct = list(tampered["ciphertext"])
    ct[0] = "A" if ct[0] != "A" else "B"     # đổi 1 ký tự base64
    tampered["ciphertext"] = "".join(ct)
    try:
        crypto.decrypt_message(tampered, bob_priv, alice_pub)
        check("Sửa ciphertext bị chặn", False)
    except (crypto.TamperError, crypto.SignatureError) as e:
        # Sửa ciphertext làm chữ ký sai TRƯỚC (verify chạy trước) -> đúng tinh thần fail-closed
        check(f"Bị chặn ({type(e).__name__})", True)

    # 5b. Giả mạo chữ ký -> SignatureError
    line("Test 3: Đổi chữ ký -> phải bị từ chối (SignatureError)")
    forged = dict(record)
    sig = list(forged["signature"])
    sig[0] = "A" if sig[0] != "A" else "B"
    forged["signature"] = "".join(sig)
    try:
        crypto.decrypt_message(forged, bob_priv, alice_pub)
        check("Giả chữ ký bị chặn", False)
    except crypto.SignatureError:
        check("Bị chặn (SignatureError)", True)

    # 5c. Sai người nhận: eve cố giải mã tin gửi cho bob
    line("Test 4: Sai người nhận (eve dùng khóa của mình) -> phải thất bại")
    try:
        crypto.decrypt_message(record, eve_priv, alice_pub)
        check("Sai người nhận bị chặn", False)
    except crypto.DecryptKeyError:
        check("Bị chặn (DecryptKeyError)", True)

    # 5d. Mỗi tin nhắn có IV + AES key khác nhau
    line("Test 5: Mỗi tin nhắn dùng IV + encrypted_key khác nhau")
    record2 = crypto.encrypt_message(fake_audio, bob_pub, alice_priv)
    check("IV khác nhau giữa 2 lần mã hóa", record["iv"] != record2["iv"])
    check("encrypted_key khác nhau (AES key mới mỗi lần)",
          record["encrypted_key"] != record2["encrypted_key"])
    check("ciphertext khác nhau dù cùng audio",
          record["ciphertext"] != record2["ciphertext"])

    line("KẾT QUẢ")
    print(f"  PASSED: {passed} | FAILED: {failed}")
    line()
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
