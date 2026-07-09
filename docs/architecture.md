# Kiến trúc & Luồng mã hóa

## 1. Tổng quan hệ thống

```
┌─────────────────────┐         REST (polling 3s)        ┌──────────────────────┐
│   Frontend (React)  │  ───────────────────────────────▶ │   Backend (FastAPI)  │
│                     │                                    │                      │
│  - MediaRecorder    │   POST /messages (audio base64)    │  crypto.py           │
│    (ghi âm)         │ ─────────────────────────────────▶ │   AES-256-GCM        │
│  - ServerView       │                                    │   RSA-OAEP / RSA-PSS │
│    (hiện ciphertext)│   GET  /messages/{user}            │                      │
│  - phát audio       │ ◀───────────────────────────────── │  db.py  ──▶ SQLite   │
└─────────────────────┘   POST /messages/{id}/decrypt      │  keystore.py ──▶ PEM │
                                                            └──────────────────────┘
```

Crypto chạy **ở backend**. Đây là **encryption at rest**, không phải E2E
(xem "Hạn chế" trong README).

---

## 2. Luồng GỬI tin nhắn (mã hóa + ký)

```mermaid
sequenceDiagram
    participant FE as Frontend (alice)
    participant API as Backend /messages
    participant CR as crypto.py
    participant DB as SQLite

    FE->>FE: MediaRecorder ghi âm -> Blob -> base64
    FE->>API: POST {sender: alice, recipient: bob, audio_base64}
    API->>CR: encrypt_message(audio, bob_pub, alice_priv)
    Note over CR: 1) AES-256 key + IV ngẫu nhiên (mới mỗi tin)
    Note over CR: 2) AES-GCM(audio) -> ciphertext + auth_tag
    Note over CR: 3) RSA-OAEP(AES key) bằng PUBLIC KEY bob -> encrypted_key
    Note over CR: 4) RSA-PSS ký ciphertext bằng PRIVATE KEY alice -> signature
    CR-->>API: {encrypted_key, iv, ciphertext, auth_tag, signature}
    API->>DB: INSERT (KHÔNG lưu audio gốc, KHÔNG lưu AES key thô)
    API-->>FE: payload đã mã hóa (hiển thị ở ServerView)
```

---

## 3. Luồng NHẬN & GIẢI MÃ (fail-closed)

```mermaid
sequenceDiagram
    participant FE as Frontend (bob)
    participant API as Backend /decrypt
    participant CR as crypto.py
    participant DB as SQLite

    FE->>API: GET /messages/bob  (polling)
    API->>DB: SELECT tin của bob
    DB-->>API: metadata + ciphertext (CHƯA giải mã)
    API-->>FE: hiển thị danh sách (chỉ ciphertext)

    FE->>API: POST /messages/{id}/decrypt  (bấm "Giải mã & phát")
    API->>CR: decrypt_message(record, bob_priv, alice_pub)
    Note over CR: a) VERIFY chữ ký RSA-PSS (alice_pub) TRƯỚC
    alt Chữ ký sai
        CR-->>API: SignatureError
        API-->>FE: 400 "Chữ ký không hợp lệ, có thể bị giả mạo" (DỪNG)
    else Chữ ký đúng
        Note over CR: b) RSA-OAEP mở AES key (bob_priv)
        Note over CR: c) AES-GCM giải mã + verify auth_tag
        alt auth_tag sai
            CR-->>API: TamperError
            API-->>FE: 400 "Dữ liệu bị sửa đổi" (DỪNG)
        else Hợp lệ
            CR-->>API: audio gốc (bytes)
            API-->>FE: audio_base64 -> phát lại
        end
    end
```

**Nguyên tắc fail-closed:** verify chữ ký + verify GCM tag PHẢI xảy ra **trước**
khi trả plaintext. Bất kỳ bước nào fail -> dừng, không lộ audio.

---

## 4. Vì sao dùng hybrid AES + RSA?

- **AES-256-GCM**: mã hóa đối xứng, nhanh, xử lý được audio lớn; GCM cho luôn
  auth tag để phát hiện sửa đổi.
- **RSA-OAEP**: RSA chỉ mã hóa được dữ liệu nhỏ, nên ta chỉ dùng RSA để **bọc
  khóa AES 32 byte** (không mã hóa trực tiếp audio). Chỉ người nhận có private
  key mới mở được khóa AES.
- **RSA-PSS**: chữ ký số chứng minh **nguồn gốc** (chỉ người gửi có private key
  ký được) và **toàn vẹn** (ký trên ciphertext).

---

## 5. Dữ liệu lưu trong DB (bảng `messages`)

| Cột | Nội dung | Ghi chú |
|-----|----------|---------|
| `encrypted_key` | RSA-OAEP(AES key), base64 | mỗi tin một key khác nhau |
| `iv` | nonce GCM 12 byte, base64 | mỗi tin một IV ngẫu nhiên |
| `ciphertext` | AES-GCM(audio), base64 | **không đọc/nghe được** |
| `auth_tag` | GCM tag 16 byte, base64 | phát hiện sửa đổi |
| `signature` | RSA-PSS trên ciphertext, base64 | xác minh nguồn gốc |

Không có cột nào chứa audio gốc hay AES key thô → **encryption at rest**.
