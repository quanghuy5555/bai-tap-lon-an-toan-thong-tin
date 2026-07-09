import { useRef, useState } from "react";

// Chuyển Blob -> chuỗi base64 (bỏ tiền tố data:...;base64,).
function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(reader.result.split(",")[1]);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

// Recorder — ghi âm bằng MediaRecorder (Web Audio API), nghe thử, rồi gửi.
export default function Recorder({ recipient, onSend, sending }) {
  const [recording, setRecording] = useState(false);
  const [previewUrl, setPreviewUrl] = useState("");
  const [err, setErr] = useState("");
  const mediaRef = useRef(null);
  const chunksRef = useRef([]);
  const blobRef = useRef(null);

  async function startRec() {
    setErr("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      chunksRef.current = [];
      mr.ondataavailable = (e) => e.data.size && chunksRef.current.push(e.data);
      mr.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: mr.mimeType || "audio/webm" });
        blobRef.current = blob;
        setPreviewUrl(URL.createObjectURL(blob));
        stream.getTracks().forEach((t) => t.stop());
      };
      mediaRef.current = mr;
      mr.start();
      setRecording(true);
    } catch (e) {
      setErr("Không truy cập được micro: " + e.message);
    }
  }

  function stopRec() {
    mediaRef.current?.stop();
    setRecording(false);
  }

  async function send() {
    if (!blobRef.current) return;
    const b64 = await blobToBase64(blobRef.current);
    await onSend(b64);
    // reset sau khi gửi
    blobRef.current = null;
    setPreviewUrl("");
  }

  return (
    <div className="panel">
      <h3>Ghi âm & gửi</h3>
      <div className="rec-row">
        {!recording ? (
          <button className="rec-btn" onClick={startRec} disabled={sending}>
            ● Ghi âm
          </button>
        ) : (
          <button className="rec-btn recording" onClick={stopRec}>
            ■ Dừng ({/* nhấp nháy */}đang ghi)
          </button>
        )}
      </div>

      {previewUrl && (
        <div className="preview">
          <span className="muted">Nghe thử:</span>
          <audio controls src={previewUrl} />
          <button
            className="send-btn"
            onClick={send}
            disabled={!recipient || sending}
          >
            {sending ? "Đang mã hóa & gửi..." : `Gửi cho ${recipient || "..."}`}
          </button>
          {!recipient && <div className="hint">Hãy chọn người nhận trước.</div>}
        </div>
      )}
      {err && <div className="error">{err}</div>}
    </div>
  );
}
