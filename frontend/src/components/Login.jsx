import { useState } from "react";
import { api } from "../api.js";

// Đăng nhập tối giản: nhập username. Nếu chưa có -> backend tự tạo + sinh khóa RSA.
export default function Login({ onLogin }) {
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function submit(e) {
    e.preventDefault();
    const username = name.trim();
    if (!username) return;
    setBusy(true);
    setErr("");
    try {
      const user = await api.createUser(username); // idempotent
      onLogin(user.username);
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <div className="login-card">
        <h1>🔐 Secure Voice Chat</h1>
        <p className="muted">
          Tin nhắn âm thanh được mã hóa <b>AES-256-GCM</b>, khóa bọc bằng{" "}
          <b>RSA-OAEP</b>, ký bằng <b>RSA-PSS</b>.
        </p>
        <form onSubmit={submit}>
          <input
            autoFocus
            placeholder="Nhập username (vd: alice)"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <button disabled={busy || !name.trim()}>
            {busy ? "Đang vào..." : "Đăng nhập / Tạo mới"}
          </button>
        </form>
        {err && <div className="error">{err}</div>}
        <p className="hint">
          Chưa có tài khoản? Nhập tên bất kỳ — hệ thống tự tạo và sinh cặp khóa RSA.
        </p>
      </div>
    </div>
  );
}
