import { useState } from "react";
import { api } from "../api.js";

// Hàng hiển thị 1 trường mã hóa (rút gọn base64).
function Field({ label, value, hint }) {
  return (
    <div className="sv-field">
      <div className="sv-label">
        {label} {hint && <span className="sv-hint">{hint}</span>}
      </div>
      <code className="sv-value">{value}</code>
    </div>
  );
}

// ServerView — ĐIỂM DEMO CHÍNH: cho thấy server chỉ lưu ciphertext base64.
export default function ServerView({ message }) {
  const [raw, setRaw] = useState(null);
  const [attack, setAttack] = useState(null);
  const [busy, setBusy] = useState(false);

  if (!message) {
    return (
      <div className="panel serverview">
        <h3>🖥️ Server View</h3>
        <p className="muted">
          Gửi một tin nhắn hoặc bấm “Xem ở Server View” trên một tin trong hộp thư
          để thấy đúng dữ liệu server lưu vào database.
        </p>
      </div>
    );
  }

  const id = message.id;
  const p = message.payload || message; // hỗ trợ cả response gửi lẫn message inbox

  async function loadRaw() {
    setBusy(true);
    try {
      setRaw(await api.raw(id));
    } finally {
      setBusy(false);
    }
  }

  async function runAttack(field) {
    setBusy(true);
    setAttack(null);
    try {
      setAttack(await api.attack(id, field));
    } catch (e) {
      setAttack({ blocked: false, detail: e.message });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="panel serverview">
      <h3>🖥️ Server View — tin #{id}</h3>
      <div className="banner">
        Đây là <b>toàn bộ</b> dữ liệu server lưu — không có audio gốc, không nghe được.
      </div>

      <Field label="encrypted_key" value={p.encrypted_key} hint="RSA-OAEP(AES key)" />
      <Field label="iv" value={p.iv} hint="nonce GCM (12B)" />
      <Field label="ciphertext" value={p.ciphertext} hint="AES-GCM(audio)" />
      <Field label="auth_tag" value={p.auth_tag} hint="GCM tag (16B)" />
      <Field label="signature" value={p.signature} hint="RSA-PSS" />

      <div className="sv-actions">
        <button className="mini" onClick={loadRaw} disabled={busy}>
          🗄️ Xem bản ghi thô trong DB
        </button>
      </div>

      {raw && (
        <pre className="raw-json">{JSON.stringify(raw, null, 2)}</pre>
      )}

      <div className="attack-box">
        <h4>🧪 Mô phỏng tấn công (không sửa DB thật)</h4>
        <div className="attack-btns">
          <button onClick={() => runAttack("ciphertext")} disabled={busy}>
            Sửa ciphertext
          </button>
          <button onClick={() => runAttack("auth_tag")} disabled={busy}>
            Sửa auth_tag (GCM)
          </button>
          <button onClick={() => runAttack("signature")} disabled={busy}>
            Giả mạo chữ ký
          </button>
        </div>
        {attack && (
          <div className={"attack-result " + (attack.blocked ? "ok" : "bad")}>
            {attack.blocked ? "✅ BỊ CHẶN" : "⚠️ KHÔNG CHẶN"}
            {attack.error_type ? ` — ${attack.error_type}` : ""}
            <div className="muted">{attack.detail}</div>
          </div>
        )}
      </div>
    </div>
  );
}
