import { useCallback, useEffect, useState } from "react";
import { api } from "./api.js";
import Login from "./components/Login.jsx";
import ContactList from "./components/ContactList.jsx";
import Recorder from "./components/Recorder.jsx";
import MessageList from "./components/MessageList.jsx";
import ServerView from "./components/ServerView.jsx";

export default function App() {
  const [me, setMe] = useState("");
  const [users, setUsers] = useState([]);
  const [recipient, setRecipient] = useState("");
  const [inbox, setInbox] = useState([]);
  const [sending, setSending] = useState(false);
  const [svMessage, setSvMessage] = useState(null); // tin đang xem ở Server View
  const [toast, setToast] = useState("");

  // Nạp danh sách user.
  const loadUsers = useCallback(async () => {
    try {
      setUsers(await api.listUsers());
    } catch (e) {
      setToast(e.message);
    }
  }, []);

  // Nạp hộp thư đến của mình (polling).
  const loadInbox = useCallback(async () => {
    if (!me) return;
    try {
      setInbox(await api.inbox(me));
    } catch (e) {
      setToast(e.message);
    }
  }, [me]);

  // Polling định kỳ: users + inbox mỗi 3s (REST thuần theo đặc tả).
  useEffect(() => {
    if (!me) return;
    loadUsers();
    loadInbox();
    const t = setInterval(() => {
      loadUsers();
      loadInbox();
    }, 3000);
    return () => clearInterval(t);
  }, [me, loadUsers, loadInbox]);

  async function handleSend(audioB64) {
    if (!recipient) return;
    setSending(true);
    setToast("");
    try {
      const res = await api.sendMessage(me, recipient, audioB64);
      setSvMessage(res); // hiện ngay payload mã hóa ở Server View
      setToast(`Đã gửi tin #${res.id} cho ${recipient} (đã mã hóa).`);
    } catch (e) {
      setToast("Lỗi gửi: " + e.message);
    } finally {
      setSending(false);
    }
  }

  // Xem 1 tin trong hộp thư ở Server View (lấy metadata mã hóa từ inbox).
  function inspect(id) {
    const m = inbox.find((x) => x.id === id);
    if (m) setSvMessage(m);
  }

  if (!me) return <Login onLogin={setMe} />;

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">🔐 Secure Voice Chat</div>
        <div className="who">
          Đang đăng nhập: <b>{me}</b>
          <button className="mini" onClick={() => setMe("")}>
            Đổi user
          </button>
        </div>
      </header>

      {toast && <div className="toast">{toast}</div>}

      <div className="layout">
        {/* KHU TRÁI — chat bình thường */}
        <div className="col left">
          <ContactList
            users={users}
            me={me}
            recipient={recipient}
            onSelect={setRecipient}
          />
          <Recorder recipient={recipient} onSend={handleSend} sending={sending} />
          <MessageList
            messages={inbox}
            onInspect={inspect}
            onRefresh={loadInbox}
          />
        </div>

        {/* KHU PHẢI — Server View (điểm demo mã hóa) */}
        <div className="col right">
          <ServerView message={svMessage} />
        </div>
      </div>
    </div>
  );
}
