import { useState } from "react";
import { api } from "../api.js";

// Chuyển base64 -> object URL để phát audio.
function b64ToAudioUrl(b64) {
  const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
  const blob = new Blob([bytes], { type: "audio/webm" });
  return URL.createObjectURL(blob);
}

// MessageList — hộp thư đến; mỗi tin có nút "Giải mã & phát".
export default function MessageList({ messages, onInspect, onRefresh }) {
  const [audioUrls, setAudioUrls] = useState({}); // id -> url
  const [errs, setErrs] = useState({}); // id -> lỗi
  const [busy, setBusy] = useState({});

  async function decryptAndPlay(id) {
    setBusy((b) => ({ ...b, [id]: true }));
    setErrs((e) => ({ ...e, [id]: "" }));
    try {
      const res = await api.decrypt(id); // server verify chữ ký + tag TRƯỚC
      const url = b64ToAudioUrl(res.audio_base64);
      setAudioUrls((m) => ({ ...m, [id]: url }));
    } catch (e) {
      setErrs((er) => ({ ...er, [id]: e.message }));
    } finally {
      setBusy((b) => ({ ...b, [id]: false }));
    }
  }

  return (
    <div className="panel">
      <div className="panel-head">
        <h3>Hộp thư đến ({messages.length})</h3>
        <button className="mini" onClick={onRefresh}>
          ⟳ Làm mới
        </button>
      </div>

      {messages.length === 0 && (
        <p className="muted">Chưa có tin nhắn nào. Nhờ người khác gửi cho bạn.</p>
      )}

      <ul className="msg-list">
        {messages.map((m) => (
          <li key={m.id} className="msg-item">
            <div className="msg-top">
              <span className="from">
                <b>{m.sender}</b> → {m.recipient}
              </span>
              <span className="msg-id">#{m.id}</span>
            </div>
            <div className="cipher-peek" title="ciphertext lưu trong DB">
              🔒 {m.ciphertext.slice(0, 40)}…
            </div>
            <div className="msg-actions">
              <button
                className="play-btn"
                onClick={() => decryptAndPlay(m.id)}
                disabled={busy[m.id]}
              >
                {busy[m.id] ? "Đang giải mã..." : "🔓 Giải mã & phát"}
              </button>
              <button className="mini" onClick={() => onInspect(m.id)}>
                👁 Xem ở Server View
              </button>
            </div>
            {audioUrls[m.id] && <audio controls src={audioUrls[m.id]} />}
            {errs[m.id] && <div className="error">⛔ {errs[m.id]}</div>}
          </li>
        ))}
      </ul>
    </div>
  );
}
