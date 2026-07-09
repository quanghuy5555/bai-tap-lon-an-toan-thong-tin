"""
main.py
-------
FastAPI app + 6 endpoint (đúng đặc tả mục 4 của build guide).

Luồng crypto chạy Ở BACKEND (server nắm khóa). Đây là encryption-at-rest,
KHÔNG phải E2E - hạn chế này ghi rõ trong README.

Chạy:
    cd backend
    .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
Swagger tự sinh tại: http://localhost:8000/docs
"""

import base64

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app import crypto, db, keystore
from app.models import (
    CreateUserRequest,
    DecryptResponse,
    EncryptedPayload,
    MessageMeta,
    SendMessageRequest,
    SendMessageResponse,
    UserResponse,
)

app = FastAPI(
    title="Secure Voice Chat API",
    description="Voice message mã hóa hybrid AES-256-GCM + RSA-2048 (OAEP + PSS).",
    version="1.0.0",
)

# CORS: cho phép frontend Vite (localhost:5173) gọi API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # demo: mở hết. Production nên giới hạn origin.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    db.init_db()


# ------------------------------------------------------------------ USERS
@app.post("/users", response_model=UserResponse, tags=["users"])
def create_user(req: CreateUserRequest):
    """
    Tạo user + sinh cặp khóa RSA-2048.
    Nếu user đã tồn tại -> trả về thông tin hiện có (idempotent, tiện demo login).
    """
    existing = db.get_user(req.username)
    if existing:
        return UserResponse(**existing)

    # Sinh cặp khóa RSA, lưu PEM ra đĩa, lấy public key để lưu DB.
    public_pem = keystore.generate_keypair(req.username)
    db.create_user(req.username, public_pem)
    user = db.get_user(req.username)
    return UserResponse(**user)


@app.get("/users", response_model=list[UserResponse], tags=["users"])
def get_users():
    """Liệt kê toàn bộ user (để frontend chọn người nhận)."""
    return [UserResponse(**u) for u in db.list_users()]


# --------------------------------------------------------------- MESSAGES
@app.post("/messages", response_model=SendMessageResponse, tags=["messages"])
def send_message(req: SendMessageRequest):
    """
    Gửi voice message:
      1. Giải base64 audio.
      2. Mã hóa AES-GCM + bọc key RSA-OAEP + ký RSA-PSS (crypto.encrypt_message).
      3. Lưu bản mã hóa vào SQLite.
      4. Trả payload đã mã hóa (để ServerView hiển thị).
    """
    sender = db.get_user(req.sender)
    recipient = db.get_user(req.recipient)
    if not sender:
        raise HTTPException(404, f"Người gửi '{req.sender}' không tồn tại.")
    if not recipient:
        raise HTTPException(404, f"Người nhận '{req.recipient}' không tồn tại.")

    try:
        audio = base64.b64decode(req.audio_base64)
    except Exception:
        raise HTTPException(400, "audio_base64 không hợp lệ.")
    if not audio:
        raise HTTPException(400, "Audio rỗng.")

    # Nạp khóa: public key người nhận (bọc AES key) + private key người gửi (ký).
    recipient_pub = keystore.public_key_from_pem(recipient["public_key"])
    sender_priv = keystore.load_private_key(req.sender)

    payload = crypto.encrypt_message(audio, recipient_pub, sender_priv)
    msg_id = db.insert_message(req.sender, req.recipient, payload)

    return SendMessageResponse(
        id=msg_id,
        sender=req.sender,
        recipient=req.recipient,
        payload=EncryptedPayload(**payload),
    )


@app.get("/messages/{username}", response_model=list[MessageMeta], tags=["messages"])
def get_messages(username: str):
    """
    Lấy tin nhắn ĐẾN của user. Trả metadata + ciphertext (CHƯA giải mã).
    Frontend polling endpoint này.
    """
    if not db.get_user(username):
        raise HTTPException(404, f"User '{username}' không tồn tại.")
    return [MessageMeta(**m) for m in db.list_messages_for(username)]


@app.post("/messages/{message_id}/decrypt", response_model=DecryptResponse,
          tags=["messages"])
def decrypt(message_id: int):
    """
    Xác minh chữ ký + giải mã 1 tin nhắn (fail-closed):
      a. verify RSA-PSS bằng public key người gửi. Sai -> 400 'chữ ký không hợp lệ'.
      b. mở AES key bằng RSA-OAEP (private key người nhận).
      c. giải mã AES-GCM, verify auth_tag. Sai -> 400 'dữ liệu bị sửa đổi'.
      d. trả audio gốc (base64).
    """
    record = db.get_message(message_id)
    if not record:
        raise HTTPException(404, "Không tìm thấy tin nhắn.")

    sender = db.get_user(record["sender"])
    if not sender:
        raise HTTPException(404, "Người gửi không còn tồn tại.")

    recipient_priv = keystore.load_private_key(record["recipient"])
    sender_pub = keystore.public_key_from_pem(sender["public_key"])

    try:
        audio = crypto.decrypt_message(record, recipient_priv, sender_pub)
    except crypto.SignatureError as e:
        # Nguồn gốc không xác thực -> từ chối rõ ràng.
        raise HTTPException(400, f"Chữ ký không hợp lệ, có thể bị giả mạo. ({e})")
    except crypto.TamperError as e:
        # Nội dung bị sửa -> GCM tag fail.
        raise HTTPException(400, f"Dữ liệu bị sửa đổi. ({e})")
    except crypto.DecryptKeyError as e:
        raise HTTPException(400, f"Không giải mã được khóa AES. ({e})")

    return DecryptResponse(
        id=message_id,
        sender=record["sender"],
        recipient=record["recipient"],
        audio_base64=base64.b64encode(audio).decode("ascii"),
        verified=True,
    )


def _flip_first_char(s: str) -> str:
    """Đổi 1 ký tự base64 đầu chuỗi để mô phỏng dữ liệu bị sửa (không đụng DB)."""
    if not s:
        return s
    return ("A" if s[0] != "A" else "B") + s[1:]


@app.post("/messages/{message_id}/attack", tags=["demo-bảo-mật"])
def attack(message_id: int, field: str = "auth_tag"):
    """
    MÔ PHỎNG TẤN CÔNG (không sửa DB thật - chỉ tấn công trên bản sao):
      - field=ciphertext : sửa 1 ký tự ciphertext  -> chữ ký sai (verify chạy trước).
      - field=auth_tag   : sửa 1 ký tự auth_tag     -> GCM tag fail (TamperError).
      - field=signature  : sửa 1 ký tự signature    -> SignatureError.
    Trả về loại lỗi + thông báo để frontend hiển thị (chứng minh fail-closed).
    """
    if field not in ("ciphertext", "auth_tag", "signature"):
        raise HTTPException(400, "field phải là ciphertext | auth_tag | signature.")

    record = db.get_message(message_id)
    if not record:
        raise HTTPException(404, "Không tìm thấy tin nhắn.")
    sender = db.get_user(record["sender"])
    if not sender:
        raise HTTPException(404, "Người gửi không còn tồn tại.")

    # Tạo bản sao và tấn công đúng 1 trường -> DB gốc KHÔNG bị đụng.
    tampered = dict(record)
    tampered[field] = _flip_first_char(tampered[field])

    recipient_priv = keystore.load_private_key(record["recipient"])
    sender_pub = keystore.public_key_from_pem(sender["public_key"])

    try:
        crypto.decrypt_message(tampered, recipient_priv, sender_pub)
        # Không bao giờ tới đây nếu crypto đúng.
        return {"blocked": False, "field": field,
                "detail": "CẢNH BÁO: giải mã vẫn thành công (không mong đợi)."}
    except crypto.SignatureError as e:
        return {"blocked": True, "field": field,
                "error_type": "SignatureError", "detail": str(e)}
    except crypto.TamperError as e:
        return {"blocked": True, "field": field,
                "error_type": "TamperError", "detail": str(e)}
    except crypto.DecryptKeyError as e:
        return {"blocked": True, "field": field,
                "error_type": "DecryptKeyError", "detail": str(e)}


@app.get("/messages/{message_id}/raw", tags=["messages"])
def get_raw(message_id: int):
    """
    Trả ĐÚNG bản ghi thô trong DB (bằng chứng server chỉ lưu 'rác' mã hóa).
    Dùng cho nút 'Xem bản ghi thô trong DB' ở ServerView.
    """
    record = db.get_message(message_id)
    if not record:
        raise HTTPException(404, "Không tìm thấy tin nhắn.")
    # Trả nguyên trạng: toàn bộ là base64 ciphertext, không có audio gốc.
    return record
