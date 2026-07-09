# 🔐 Secure Voice Message Chat

Ứng dụng chat cho phép gửi **tin nhắn âm thanh (voice message)** đã được **mã hóa**.
Nội dung audio được mã hóa **AES-256-GCM**, khóa AES được bọc bằng **RSA-2048-OAEP**,
và tính toàn vẹn/nguồn gốc được bảo đảm bằng **chữ ký số RSA-2048-PSS**.

> **Điểm demo cốt lõi:** Khi mở database (`backend/data.db`) hoặc xem payload API,
> ta chỉ thấy **ciphertext base64 vô nghĩa** — KHÔNG nghe/đọc được audio gốc.

---

## 1. Kiến trúc & thuật toán

| Thành phần | Lựa chọn |
|-----------|----------|
| Backend | Python + FastAPI |
| Giao tiếp | REST API thuần (frontend polling mỗi 3s) |
| Vị trí crypto | **Backend** (server mã hóa/giải mã) |
| Lưu trữ | SQLite — audio lưu ở dạng đã mã hóa (encryption at rest) |
| Frontend | React (Vite) + Web Audio API (MediaRecorder) |
| Thư viện crypto | `cryptography` (pyca) |

**Thuật toán (chốt cứng):**
- **AES-256-GCM** — mã hóa nội dung audio (confidentiality + integrity qua auth tag).
- **RSA-2048 + OAEP (SHA-256)** — bọc (mã hóa) khóa AES session của từng tin nhắn.
- **RSA-2048 + PSS (SHA-256)** — ký & xác minh (chống giả mạo nguồn gốc).

Mỗi tin nhắn dùng **AES key + IV mới, ngẫu nhiên** (không tái sử dụng).

---

## 2. Yêu cầu môi trường

- **Python 3.10+** (đã test với 3.12)
- **Node.js 18+** và npm (đã test với Node 24)
- Trình duyệt hỗ trợ `MediaRecorder` + micro (Chrome/Edge/Firefox)

> ⚠️ Ghi âm cần **micro** và trang chạy ở `localhost` (secure context) để trình
> duyệt cho phép `getUserMedia`.

---

## 3. Cài đặt & chạy

### 3.1. Backend

```bash
cd backend

# Tạo virtualenv
python -m venv .venv

# Kích hoạt venv
#   Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
#   macOS/Linux:
#   source .venv/bin/activate

# Cài thư viện
pip install -r requirements.txt

# Chạy server (Swagger tại http://localhost:8000/docs)
python -m uvicorn app.main:app --reload --port 8000
```

> Trên Windows nếu không activate venv, có thể gọi trực tiếp:
> `.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000`

### 3.2. Frontend

Mở terminal thứ 2:

```bash
cd frontend
npm install
npm run dev      # mở http://localhost:5173
```

### 3.3. Tài khoản demo

Không có mật khẩu. Chỉ cần **nhập username** — nếu chưa tồn tại, hệ thống tự tạo
và sinh cặp khóa RSA. Để thử gửi/nhận:

1. Tab 1: đăng nhập **`alice`**.
2. Tab 2 (cửa sổ ẩn danh hoặc trình duyệt khác): đăng nhập **`bob`**.
3. Ở tab alice: chọn người nhận **bob** → **Ghi âm** → **Gửi**.
4. Ở tab bob: đợi tối đa 3s (polling) → bấm **🔓 Giải mã & phát**.

---

## 4. Kiểm chứng "encryption at rest"

Mở `backend/data.db` bằng **DB Browser for SQLite** → bảng `messages`:
- Cột `ciphertext`, `encrypted_key`, `auth_tag`, `signature` toàn **base64 rác**.
- **KHÔNG** có cột audio gốc, **KHÔNG** có AES key dạng thô.

Hoặc dùng panel **Server View** trong app + nút **"Xem bản ghi thô trong DB"**
(gọi `GET /messages/{id}/raw`).

---

## 5. Test tự động

```bash
cd backend
python test_crypto.py     # PHASE 1 - crypto core (8 test)
python test_api.py        # PHASE 2 - API + DB (cần server đang chạy)
```

Xem chi tiết ở [docs/test-report.md](docs/test-report.md).

### Video demo tự động (Playwright)

`demo/demo.webm` — video chạy tự động toàn bộ luồng (ghi âm bằng fake mic → gửi →
Server View → mô phỏng tấn công → giải mã & phát). Cách quay lại: xem
[demo/README.md](demo/README.md).

---

## 6. API tóm tắt

| Method | Path | Mô tả |
|--------|------|-------|
| POST | `/users` | Tạo user + sinh cặp RSA. |
| GET | `/users` | Liệt kê users. |
| POST | `/messages` | Gửi voice message (mã hóa + ký + lưu). |
| GET | `/messages/{username}` | Tin nhắn đến (ciphertext, chưa giải mã). |
| POST | `/messages/{id}/decrypt` | Xác minh chữ ký + giải mã, trả audio. |
| GET | `/messages/{id}/raw` | Bản ghi thô trong DB (bằng chứng chỉ lưu rác). |
| POST | `/messages/{id}/attack?field=…` | Mô phỏng tấn công (không sửa DB thật). |

---

## 7. Giả định & Hạn chế đã biết

Phần này **phải** được nêu trong báo cáo/bảo vệ, KHÔNG che giấu.

1. **KHÔNG phải mã hóa đầu-cuối (E2E) thật.**
   Vì crypto chạy ở **backend**, server nắm cả private key và về lý thuyết
   đọc được plaintext. Cái ta chứng minh được là **encryption at rest**
   (dữ liệu trong DB bị mã hóa) và **luồng hybrid AES+RSA hoạt động đúng**.
   *Hướng nâng cấp:* chuyển toàn bộ crypto sang **client** (dùng Web Crypto API),
   server chỉ lưu ciphertext → đạt E2E thật.

2. **Auth tối giản, không chống mạo danh.**
   "Đăng nhập" chỉ là nhập username; định danh qua username trong request.
   Đề tài tập trung vào **crypto tin nhắn**, không phải access control.
   *Nâng cấp:* thêm mật khẩu/JWT, ràng buộc private key với phiên đăng nhập.

3. **Private key lưu plaintext trên đĩa** (`backend/keys/*_private.pem`).
   Chấp nhận cho demo. *Production:* mã hóa PEM bằng passphrase
   (`BestAvailableEncryption`), hoặc dùng HSM/KMS.

4. **CORS mở `*`** cho tiện demo. Production nên giới hạn origin.

---

## 8. Cấu trúc thư mục

```
secure-voice-chat/
├── backend/
│   ├── app/
│   │   ├── main.py        # FastAPI + 6 endpoint (+ endpoint mô phỏng tấn công)
│   │   ├── crypto.py      # AES-256-GCM + RSA-OAEP + RSA-PSS
│   │   ├── db.py          # SQLite schema + queries
│   │   ├── models.py      # Pydantic models
│   │   └── keystore.py    # Sinh & nạp cặp khóa RSA
│   ├── test_crypto.py     # Test PHASE 1
│   ├── test_api.py        # Test PHASE 2
│   ├── requirements.txt
│   ├── keys/              # (gitignored) private/public PEM
│   └── data.db            # (gitignored) SQLite
├── frontend/              # React + Vite
│   └── src/
│       ├── App.jsx
│       ├── api.js
│       └── components/    # Login, ContactList, Recorder, MessageList, ServerView
├── docs/
│   ├── architecture.md    # Sơ đồ luồng mã hóa (mermaid)
│   └── test-report.md     # Bảng test case
└── .gitignore             # loại keys/, *.db, *.pem, node_modules/, __pycache__/
```

**Bảo mật git:** `.gitignore` đã loại `keys/`, `*.pem`, `*.db`. **Tuyệt đối không
commit private key.**
https://github.com/quanghuy5555/bai-tap-lon-an-toan-thong-tin.git