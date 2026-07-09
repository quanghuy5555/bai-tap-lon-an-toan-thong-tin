# Demo tự động (Playwright) + Video

`demo.webm` là video demo chạy tự động toàn bộ luồng, quay bằng Playwright.
Mở bằng trình duyệt (Chrome/Edge/Firefox) hoặc VLC.

## Video quay những gì?

1. Tạo user `bob` (sinh cặp khóa RSA-2048).
2. Đăng nhập `alice`, chọn người nhận `bob`.
3. **Ghi âm** (dùng *fake microphone* của Chromium) → **Gửi**.
4. **Server View**: hiện toàn bộ dữ liệu server lưu — `encrypted_key / iv /
   ciphertext / auth_tag / signature` (toàn base64 rác) + bản ghi thô trong DB.
5. **Mô phỏng tấn công**:
   - Sửa `auth_tag` → `TamperError` (GCM tag fail).
   - Giả mạo `signature` → `SignatureError`.
6. Đổi user sang `bob` → **Giải mã & phát** lại audio của alice.

Mỗi bước có caption nổi để video tự giải thích.

## Chạy lại demo

Cần **backend (:8000)** và **frontend (:5173)** đang chạy (xem README gốc), rồi:

```bash
cd backend
# cài 1 lần
.venv/Scripts/python.exe -m pip install playwright
.venv/Scripts/python.exe -m playwright install chromium
# chạy demo -> tạo demo/demo.webm
.venv/Scripts/python.exe ../demo/demo_playwright.py
```

> Script dùng cờ Chromium `--use-fake-device-for-media-stream` +
> `--use-fake-ui-for-media-stream` nên `getUserMedia`/`MediaRecorder` ghi được
> âm thanh giả mà không cần micro thật → chạy headless, không cần thao tác tay.
>
> Muốn xem trực quan lúc chạy: sửa `headless=True` → `headless=False` trong
> `demo_playwright.py`.

## Đổi sang MP4 (tùy chọn)

`demo.webm` phát tốt trên trình duyệt/VLC. Nếu cần nhúng PowerPoint, convert:

```bash
ffmpeg -i demo.webm demo.mp4
```
