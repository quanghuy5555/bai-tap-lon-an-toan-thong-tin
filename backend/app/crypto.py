"""
crypto.py
---------
Toàn bộ logic mật mã hybrid AES + RSA cho voice message.

Sơ đồ tổng quát (mỗi tin nhắn):
    1. Sinh AES-256 key ngẫu nhiên (32 bytes) + nonce/IV ngẫu nhiên (12 bytes).
    2. Mã hóa audio bằng AES-256-GCM -> ciphertext + auth_tag (tính toàn vẹn).
    3. Bọc (mã hóa) AES key bằng RSA-OAEP với PUBLIC KEY của người NHẬN.
    4. Ký ciphertext bằng RSA-PSS với PRIVATE KEY của người GỬI (chống giả mạo/chống chối bỏ).

Khi giải mã, thứ tự BẮT BUỘC (fail-closed):
    a. Xác minh chữ ký (public key người gửi) TRƯỚC.  Sai -> DỪNG.
    b. Mở khóa AES key bằng RSA-OAEP (private key người nhận).
    c. Giải mã AES-GCM, verify auth_tag.  Sai -> DỪNG.
    d. Chỉ khi tất cả PASS mới trả plaintext.

Thuật toán chốt cứng:
    - AES-256-GCM           : nội dung audio
    - RSA-2048 + OAEP/SHA256 : bọc AES key
    - RSA-2048 + PSS/SHA256  : chữ ký số
"""

import base64
import os

from cryptography.exceptions import InvalidSignature, InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Kích thước tham số (bytes)
AES_KEY_SIZE = 32        # AES-256
GCM_NONCE_SIZE = 12      # nonce/IV khuyến nghị cho GCM
GCM_TAG_SIZE = 16        # auth tag GCM (128-bit)


# ----------------------------- Tiện ích base64 -----------------------------
def _b64e(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _b64d(text: str) -> bytes:
    return base64.b64decode(text.encode("ascii"))


# ----------------------------- Lỗi nghiệp vụ -------------------------------
class SignatureError(Exception):
    """Chữ ký không hợp lệ -> tin nhắn có thể bị giả mạo nguồn gốc."""


class TamperError(Exception):
    """Auth tag GCM sai -> nội dung ciphertext đã bị sửa đổi."""


class DecryptKeyError(Exception):
    """Không mở được AES key bằng RSA-OAEP (sai private key / key hỏng)."""


# ----------------------------- Mã hóa (GỬI) --------------------------------
def encrypt_message(audio: bytes, recipient_public_key, sender_private_key) -> dict:
    """
    Mã hóa + ký một voice message.

    Tham số:
        audio                : bytes audio gốc (đã giải base64 ở tầng API).
        recipient_public_key : đối tượng RSA public key của NGƯỜI NHẬN.
        sender_private_key   : đối tượng RSA private key của NGƯỜI GỬI.

    Trả về dict các trường base64 (đúng những gì server lưu vào DB):
        encrypted_key, iv, ciphertext, auth_tag, signature
    """
    # (a) Sinh AES key + nonce/IV MỚI, NGẪU NHIÊN cho từng tin nhắn (không tái sử dụng).
    aes_key = os.urandom(AES_KEY_SIZE)
    iv = os.urandom(GCM_NONCE_SIZE)

    # (b) Mã hóa audio bằng AES-256-GCM.
    #     AESGCM.encrypt trả về (ciphertext || auth_tag) nối liền; tag = 16 bytes cuối.
    aesgcm = AESGCM(aes_key)
    ct_and_tag = aesgcm.encrypt(iv, audio, None)  # associated_data = None
    ciphertext = ct_and_tag[:-GCM_TAG_SIZE]
    auth_tag = ct_and_tag[-GCM_TAG_SIZE:]

    # (c) Bọc AES key bằng RSA-OAEP (public key người nhận) -> chỉ người nhận mở được.
    encrypted_key = recipient_public_key.encrypt(
        aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

    # (d) Ký ciphertext bằng RSA-PSS (private key người gửi).
    #     Truyền hashes.SHA256() => thư viện tự băm ciphertext trước khi ký,
    #     tức chữ ký được đặt trên SHA-256(ciphertext) đúng như yêu cầu.
    signature = sender_private_key.sign(
        ciphertext,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )

    return {
        "encrypted_key": _b64e(encrypted_key),
        "iv": _b64e(iv),
        "ciphertext": _b64e(ciphertext),
        "auth_tag": _b64e(auth_tag),
        "signature": _b64e(signature),
    }


# ----------------------------- Giải mã (NHẬN) ------------------------------
def decrypt_message(record: dict, recipient_private_key, sender_public_key) -> bytes:
    """
    Xác minh chữ ký rồi giải mã một voice message (fail-closed).

    Tham số:
        record               : dict có các trường base64
                               (encrypted_key, iv, ciphertext, auth_tag, signature).
        recipient_private_key: private key RSA của NGƯỜI NHẬN (mở AES key).
        sender_public_key    : public key RSA của NGƯỜI GỬI (xác minh chữ ký).

    Trả về: bytes audio gốc.

    Ném lỗi:
        SignatureError  - chữ ký sai (giả mạo nguồn gốc).
        TamperError     - auth tag sai (nội dung bị sửa).
        DecryptKeyError - không mở được AES key.
    """
    encrypted_key = _b64d(record["encrypted_key"])
    iv = _b64d(record["iv"])
    ciphertext = _b64d(record["ciphertext"])
    auth_tag = _b64d(record["auth_tag"])
    signature = _b64d(record["signature"])

    # (a) XÁC MINH CHỮ KÝ TRƯỚC TIÊN. Nếu sai -> dừng, không giải mã gì cả.
    try:
        sender_public_key.verify(
            signature,
            ciphertext,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
    except InvalidSignature:
        raise SignatureError("Chữ ký không hợp lệ - tin nhắn có thể bị giả mạo.")

    # (b) Mở khóa AES key bằng RSA-OAEP (private key người nhận).
    try:
        aes_key = recipient_private_key.decrypt(
            encrypted_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
    except ValueError:
        raise DecryptKeyError("Không mở được khóa AES (sai khóa hoặc dữ liệu hỏng).")

    # (c) Giải mã AES-GCM. Ghép lại (ciphertext || auth_tag) để thư viện verify tag.
    #     Nếu ciphertext hoặc tag bị sửa -> InvalidTag.
    aesgcm = AESGCM(aes_key)
    try:
        audio = aesgcm.decrypt(iv, ciphertext + auth_tag, None)
    except InvalidTag:
        raise TamperError("Auth tag không khớp - dữ liệu đã bị sửa đổi.")

    # (d) Tất cả PASS -> trả plaintext audio.
    return audio
