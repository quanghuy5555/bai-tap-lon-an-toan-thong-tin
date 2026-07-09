"""
models.py
---------
Pydantic models cho request/response của API.
Giữ tối giản, chỉ khai báo các trường thực sự cần.
"""

from pydantic import BaseModel, Field


# ------------------------------- Requests ----------------------------------
class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=32)


class SendMessageRequest(BaseModel):
    sender: str
    recipient: str
    audio_base64: str = Field(..., description="Audio gốc, đã encode base64.")


# ------------------------------- Responses ---------------------------------
class UserResponse(BaseModel):
    username: str
    public_key: str
    created_at: str | None = None


class EncryptedPayload(BaseModel):
    """Đúng những gì server lưu vào DB cho 1 tin nhắn (dạng mã hóa)."""
    encrypted_key: str
    iv: str
    ciphertext: str
    auth_tag: str
    signature: str


class MessageMeta(EncryptedPayload):
    """Metadata + payload mã hóa, KHÔNG kèm audio giải mã."""
    id: int
    sender: str
    recipient: str
    created_at: str | None = None


class SendMessageResponse(BaseModel):
    id: int
    sender: str
    recipient: str
    payload: EncryptedPayload


class DecryptResponse(BaseModel):
    id: int
    sender: str
    recipient: str
    audio_base64: str
    verified: bool = True
