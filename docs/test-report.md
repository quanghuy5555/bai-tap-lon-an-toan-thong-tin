# Báo cáo Kiểm thử — Secure Voice Chat

Môi trường test: Windows 11, Python 3.12.10, Node 24, `cryptography` 44.0.0.
Ngày: 2026-07-09.

Cách chạy lại:

```bash
cd backend
python test_crypto.py                          # PHASE 1
python -m uvicorn app.main:app --port 8000     # (terminal khác) khởi động server
python test_api.py                             # PHASE 2 (cần server chạy)
```

---

## 1. Test chức năng (functional)

| # | Test case | Cách kiểm | Kỳ vọng | Kết quả |
|---|-----------|-----------|---------|---------|
| F1 | Tạo user + sinh khóa RSA | POST `/users` (alice, bob) | Trả public key PEM, tạo file `keys/*.pem` | ✅ PASS |
| F2 | Liệt kê user | GET `/users` | Có alice, bob | ✅ PASS |
| F3 | Gửi voice message | POST `/messages` | 200 + payload 5 trường mã hóa | ✅ PASS |
| F4 | Round-trip mã hóa→giải mã | encrypt rồi decrypt "audio" giả | audio khôi phục **khớp byte-for-byte** | ✅ PASS |
| F5 | Nhận danh sách tin (chưa giải mã) | GET `/messages/bob` | Có metadata + ciphertext, KHÔNG có audio | ✅ PASS |
| F6 | Giải mã hợp lệ | POST `/messages/{id}/decrypt` | 200 + audio_base64 khớp gốc | ✅ PASS |
| F7 | End-to-end trên UI | Ghi âm → gửi → nhận → phát (thủ công) | Nghe lại đúng giọng | ✅ PASS (UI + API) |

> F7: đã kiểm chứng luồng UI (login, danh sách người nhận, ServerView, giải mã,
> mô phỏng tấn công) chạy thật trên trình duyệt; phần mã hóa/giải mã audio thật
> đã kiểm chứng qua `test_api.py` với dữ liệu audio thật (bytes).

---

## 2. Test bảo mật (security / fail-closed)

| # | Test case | Cách tấn công | Kỳ vọng | Kết quả |
|---|-----------|---------------|---------|---------|
| S1 | **Encryption at rest** | Đọc trực tiếp `data.db` | ciphertext là base64 rác, KHÔNG có audio gốc / AES key thô | ✅ PASS |
| S2 | **Sửa ciphertext** | Đổi 1 ký tự cột `ciphertext` rồi decrypt | Bị từ chối (chữ ký verify trước → `SignatureError`) | ✅ PASS |
| S3 | **Sửa auth_tag (GCM)** | Đổi 1 ký tự `auth_tag` (chữ ký vẫn hợp lệ) | GCM tag fail → `TamperError` | ✅ PASS |
| S4 | **Giả mạo chữ ký** | Đổi 1 ký tự `signature` | `SignatureError`, dừng trước khi giải mã | ✅ PASS |
| S5 | **Sai người nhận** | eve dùng private key của mình để mở tin gửi cho bob | RSA-OAEP fail → `DecryptKeyError` | ✅ PASS |
| S6 | **AES key + IV không tái sử dụng** | Mã hóa cùng 1 audio 2 lần | `iv`, `encrypted_key`, `ciphertext` khác nhau hoàn toàn | ✅ PASS |
| S7 | **Fail-closed thứ tự** | (S2–S4) | Không có plaintext nào bị trả khi verify fail | ✅ PASS |

### Ghi chú về S2 vs S3
Khi **sửa ciphertext** (S2), lỗi báo là `SignatureError` chứ không phải
`TamperError` — vì chữ ký được đặt trên ciphertext và được **verify trước tiên**,
nên phát hiện sai lệch trước cả bước kiểm GCM tag. Đây đúng tinh thần fail-closed:
dữ liệu vẫn bị từ chối. Để minh họa riêng lỗi **GCM tag**, dùng S3 (sửa `auth_tag`,
giữ chữ ký hợp lệ) → nhận đúng `TamperError`.

Cả 3 kịch bản tấn công (S2, S3, S4) đều có nút bấm trực quan trong panel
**Server View → "Mô phỏng tấn công"** (gọi `POST /messages/{id}/attack`),
thao tác trên **bản sao**, KHÔNG làm hỏng bản ghi gốc trong DB.

---

## 3. Kết quả tự động

```
PHASE 1 — test_crypto.py : PASSED 8 | FAILED 0
PHASE 2 — test_api.py    : PASSED 10 | FAILED 0
PHASE 4 — attack (3 field): ciphertext→SignatureError, auth_tag→TamperError,
                            signature→SignatureError ; DB không bị đụng
```

---

## 4. Đối chiếu Definition of Done

| Tiêu chí | Trạng thái |
|----------|-----------|
| Ghi âm → gửi → nhận → giải mã → phát lại đúng giọng | ✅ |
| Mở `data.db` thấy audio là ciphertext base64, không nghe được | ✅ (S1) |
| Chữ ký sai → giải mã bị từ chối, thông báo rõ ràng | ✅ (S4) |
| Sửa ciphertext / auth_tag → GCM/chữ ký reject | ✅ (S2, S3) |
| Mỗi tin có IV + AES key khác nhau | ✅ (S6) |
| README chạy được không cần hỏi | ✅ |
| `.gitignore` loại keys + db + node_modules | ✅ |
