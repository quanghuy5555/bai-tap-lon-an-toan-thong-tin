"""Chụp screenshot UI thật để nhúng vào slide."""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

URL = "http://localhost:5173"
OUT = Path(r"C:\Users\Admin\AppData\Local\Temp\claude\C--Users-Admin-OneDrive-Desktop-baitaplon09072026\cd2f1f03-2d3a-46bb-b93a-eb21ad9b50cd\scratchpad\deck\assets")
OUT.mkdir(parents=True, exist_ok=True)
VP = {"width": 1440, "height": 960}


def main():
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True, args=[
            "--use-fake-device-for-media-stream",
            "--use-fake-ui-for-media-stream",
            "--autoplay-policy=no-user-gesture-required",
        ])
        ctx = b.new_context(viewport=VP, permissions=["microphone"],
                            device_scale_factor=2)
        p = ctx.new_page()
        p.set_default_timeout(15000)
        p.goto(URL)

        # tạo bob
        p.fill("input", "bob"); p.get_by_role("button", name="Đăng nhập / Tạo mới").click()
        p.wait_for_selector(".topbar"); p.get_by_role("button", name="Đổi user").click()
        p.wait_for_selector(".login-card")
        # login alice
        p.fill("input", "alice"); p.get_by_role("button", name="Đăng nhập / Tạo mới").click()
        p.wait_for_selector(".topbar")
        p.wait_for_timeout(3500)
        p.locator(".contact", has_text="bob").click()
        # ghi âm + gửi
        p.get_by_role("button", name="Ghi âm").click(); p.wait_for_timeout(2200)
        p.locator(".rec-btn").click(); p.wait_for_selector(".preview audio")
        p.locator(".send-btn").click(); p.wait_for_selector(".serverview .sv-value")
        p.wait_for_timeout(800)

        # 1) overview full page (alice, server view populated)
        p.screenshot(path=str(OUT / "app_overview.png"))
        # 2) server view element
        p.locator(".serverview").screenshot(path=str(OUT / "server_view.png"))
        # 3) attack: chạy auth_tag
        p.locator(".attack-btns button", has_text="auth_tag").click()
        p.wait_for_selector(".attack-result"); p.wait_for_timeout(400)
        p.locator(".attack-box").screenshot(path=str(OUT / "attack.png"))

        # 4) bob inbox + giải mã & phát
        p.get_by_role("button", name="Đổi user").click(); p.wait_for_selector(".login-card")
        p.fill("input", "bob"); p.get_by_role("button", name="Đăng nhập / Tạo mới").click()
        p.wait_for_selector(".topbar"); p.wait_for_timeout(500)
        p.locator(".play-btn").first.click(); p.wait_for_selector(".msg-item audio")
        p.wait_for_timeout(600)
        p.locator(".left").screenshot(path=str(OUT / "inbox.png"))

        ctx.close(); b.close()
    for f in ["app_overview", "server_view", "attack", "inbox"]:
        print("saved", (OUT / (f + ".png")))


if __name__ == "__main__":
    main()
