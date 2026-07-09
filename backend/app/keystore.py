"""
keystore.py
-----------
Quản lý cặp khóa RSA-2048 cho mỗi user.

- Sinh cặp khóa RSA-2048 khi user được tạo.
- Lưu private key ra file PEM: keys/{username}_private.pem
- Lưu public key ra file PEM: keys/{username}_public.pem
- Nạp lại khóa từ đĩa khi cần mã hóa/giải mã/ký/xác minh.

LƯU Ý BẢO MẬT (ghi trong báo cáo): private key được lưu dạng plaintext
trên đĩa cho mục đích demo. Production cần mã hóa PEM bằng passphrase
(BestAvailableEncryption).
"""

from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# Thư mục lưu khóa: backend/keys/
KEYS_DIR = Path(__file__).resolve().parent.parent / "keys"
KEYS_DIR.mkdir(parents=True, exist_ok=True)


def _private_path(username: str) -> Path:
    return KEYS_DIR / f"{username}_private.pem"


def _public_path(username: str) -> Path:
    return KEYS_DIR / f"{username}_public.pem"


def user_keys_exist(username: str) -> bool:
    """Kiểm tra user đã có cặp khóa trên đĩa chưa."""
    return _private_path(username).exists() and _public_path(username).exists()


def generate_keypair(username: str) -> str:
    """
    Sinh cặp khóa RSA-2048 cho user và lưu ra đĩa dạng PEM.
    Trả về public key PEM (chuỗi) để lưu vào bảng users trong DB.
    """
    # Sinh khóa riêng RSA-2048 (public exponent 65537 là chuẩn khuyến nghị)
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Serialize private key -> PEM (PKCS8, KHÔNG mã hóa - chỉ dùng cho demo)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    # Serialize public key -> PEM (SubjectPublicKeyInfo)
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    _private_path(username).write_bytes(private_pem)
    _public_path(username).write_bytes(public_pem)

    return public_pem.decode("utf-8")


def load_private_key(username: str):
    """Nạp private key RSA của user từ đĩa (dùng để giải mã / ký)."""
    pem = _private_path(username).read_bytes()
    return serialization.load_pem_private_key(pem, password=None)


def load_public_key_pem(username: str) -> str:
    """Nạp public key PEM (chuỗi) của user từ đĩa."""
    return _public_path(username).read_text(encoding="utf-8")


def public_key_from_pem(pem: str):
    """Chuyển public key PEM (chuỗi) -> đối tượng public key để dùng crypto."""
    return serialization.load_pem_public_key(pem.encode("utf-8"))
