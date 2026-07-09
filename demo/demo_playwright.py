"""
demo_playwright.py
------------------
Chạy tự động toàn bộ luồng demo Secure Voice Chat bằng Playwright và QUAY VIDEO.

- Dùng Chromium với "fake media device" -> getUserMedia/MediaRecorder ghi được
  âm thanh giả (tone) mà không cần micro thật -> chạy được headless.
- Kịch bản một mạch (1 trang -> 1 video liền):
    1. Đăng nhập bob (tạo user + khóa RSA), rồi đổi user.
    2. Đăng nhập alice -> chọn người nhận bob.
    3. Ghi âm (fake mic) -> Gửi. Server View hiện ciphertext (base64 rác).
    4. Mô phỏng tấn công auth_tag -> TamperError (bị chặn).
    5. Đổi user sang bob -> Giải mã & phát tin của alice.
- Video .webm được lưu ở demo/videos/ rồi đổi tên thành demo/demo.webm.

Yêu cầu: backend chạy ở :8000, frontend ở :5173.
    cd backend
    .venv/Scripts/python.exe -m playwright install chromium
    .venv/Scripts/python.exe ../demo/demo_playwright.py
"""

import shutil
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

URL = "http://localhost:5173"
HERE = Path(__file__).resolve().parent
VID_DIR = HERE / "videos"
VID_DIR.mkdir(exist_ok=True)

VIEWPORT = {"width": 1360, "height": 900}


def caption(page, text, sub=""):
    """Chèn/cập nhật một caption nổi để video tự giải thích từng bước."""
    page.evaluate(
        """([text, sub]) => {
            let el = document.getElementById('demo-caption');
            if (!el) {
                el = document.createElement('div');
                el.id = 'demo-caption';
                el.style.cssText = 'position:fixed;left:50%;bottom:24px;transform:translateX(-50%);'
                  + 'z-index:99999;background:rgba(10,12,24,.92);border:1px solid #6c8cff;'
                  + 'border-radius:12px;padding:12px 22px;color:#e7e9f5;font-family:system-ui;'
                  + 'font-size:18px;font-weight:600;box-shadow:0 8px 30px rgba(0,0,0,.5);'
                  + 'text-align:center;max-width:80vw;';
                document.body.appendChild(el);
            }
            el.innerHTML = text + (sub ? ('<div style=\"font-size:13px;font-weight:400;'
                + 'color:#9aa0c0;margin-top:4px\">' + sub + '</div>') : '');
        }""",
        [text, sub],
    )


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=[
                "--use-fake-device-for-media-stream",   # cấp audio track giả
                "--use-fake-ui-for-media-stream",        # tự đồng ý quyền micro
                "--autoplay-policy=no-user-gesture-required",
            ],
        )
        context = browser.new_context(
            viewport=VIEWPORT,
            record_video_dir=str(VID_DIR),
            record_video_size=VIEWPORT,
            permissions=["microphone"],
        )
        page = context.new_page()
        page.set_default_timeout(15000)

        def step(msg, sub="", pause=1200):
            print(f"[demo] {msg}")
            caption(page, msg, sub)
            page.wait_for_timeout(pause)

        page.goto(URL)
        step("🔐 Secure Voice Chat — demo tự động",
             "Mã hóa AES-256-GCM + RSA-2048 (OAEP + PSS)", 1800)

        # 1) Tạo user bob trước để alice có người nhận
        step("Bước 1: Tạo user 'bob' (tự sinh cặp khóa RSA-2048)")
        page.fill("input", "bob")
        page.get_by_role("button", name="Đăng nhập / Tạo mới").click()
        page.wait_for_selector(".topbar")
        page.wait_for_timeout(1000)
        page.get_by_role("button", name="Đổi user").click()
        page.wait_for_selector(".login-card")

        # 2) Đăng nhập alice
        step("Bước 2: Đăng nhập 'alice' (người gửi)")
        page.fill("input", "alice")
        page.get_by_role("button", name="Đăng nhập / Tạo mới").click()
        page.wait_for_selector(".topbar")

        # Chờ polling nạp danh bạ rồi chọn bob
        step("Bước 3: Chọn người nhận 'bob'", "Danh bạ nạp qua polling REST 3s", 3500)
        page.locator(".contact", has_text="bob").click()
        page.wait_for_timeout(800)

        # 3) Ghi âm bằng fake mic
        step("Bước 4: Ghi âm (dùng fake microphone)", "MediaRecorder → audio blob")
        page.get_by_role("button", name="Ghi âm").click()
        page.wait_for_timeout(2600)  # thu ~2.6s
        page.locator(".rec-btn").click()  # Dừng
        page.wait_for_selector(".preview audio")
        step("Ghi âm xong — nghe thử được trước khi gửi", pause=1500)

        # Gửi -> backend mã hóa + ký + lưu
        step("Bước 5: Gửi → server mã hóa AES + bọc key RSA + ký RSA-PSS")
        page.locator(".send-btn").click()
        page.wait_for_selector(".serverview .sv-value")
        step("Server View: đây là TOÀN BỘ dữ liệu server lưu",
             "encrypted_key / iv / ciphertext / auth_tag / signature — toàn base64 rác",
             2600)

        # Xem bản ghi thô trong DB
        page.get_by_role("button", name="Xem bản ghi thô trong DB").click()
        page.wait_for_selector(".raw-json")
        step("Bản ghi thô trong SQLite — KHÔNG có audio gốc", pause=2600)

        # 4) Mô phỏng tấn công auth_tag -> TamperError
        step("Bước 6: Mô phỏng tấn công — sửa auth_tag (GCM)")
        page.locator(".attack-btns button", has_text="auth_tag").click()
        page.wait_for_selector(".attack-result")
        page.wait_for_timeout(400)
        result = page.locator(".attack-result").inner_text()
        step("Kết quả tấn công: " + result.replace("\n", " — "),
             "Fail-closed: dữ liệu bị sửa → từ chối", 2800)

        # Tấn công giả chữ ký
        step("Tiếp: giả mạo chữ ký (signature)")
        page.locator(".attack-btns button", has_text="Giả mạo chữ ký").click()
        page.wait_for_timeout(700)
        result2 = page.locator(".attack-result").inner_text()
        step("Kết quả: " + result2.replace("\n", " — "), pause=2600)

        # 5) Đổi sang bob, giải mã & phát
        step("Bước 7: Đăng nhập 'bob' (người nhận) để giải mã")
        page.get_by_role("button", name="Đổi user").click()
        page.wait_for_selector(".login-card")
        page.fill("input", "bob")
        page.get_by_role("button", name="Đăng nhập / Tạo mới").click()
        page.wait_for_selector(".topbar")
        step("Hộp thư của bob: tin đến vẫn ở dạng 🔒 ciphertext", pause=2500)

        step("Bấm 'Giải mã & phát' → server verify chữ ký + tag TRƯỚC")
        page.locator(".play-btn").first.click()
        page.wait_for_selector(".msg-item audio")
        step("✅ Giải mã thành công → phát lại audio gốc", "Round-trip AES+RSA hoạt động đúng", 3000)

        step("Hoàn tất demo 🎉",
             "Encryption-at-rest + hybrid AES/RSA + chữ ký số + fail-closed", 2500)

        # Kết thúc: đóng context để lưu video
        video_path = page.video.path()
        context.close()
        browser.close()

    # Đổi tên video -> demo/demo.webm
    out = HERE / "demo.webm"
    shutil.copyfile(video_path, out)
    print(f"[demo] Video đã lưu: {out}")
    print(f"[demo] (bản gốc Playwright: {video_path})")


if __name__ == "__main__":
    main()
