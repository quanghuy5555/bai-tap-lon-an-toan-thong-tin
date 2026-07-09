// ContactList — chọn người nhận (loại chính mình khỏi danh sách).
export default function ContactList({ users, me, recipient, onSelect }) {
  const others = users.filter((u) => u.username !== me);
  return (
    <div className="panel">
      <h3>Người nhận</h3>
      {others.length === 0 ? (
        <p className="muted">
          Chưa có user khác. Mở tab thứ 2, đăng nhập bằng tên khác để có người nhận.
        </p>
      ) : (
        <div className="contact-list">
          {others.map((u) => (
            <button
              key={u.username}
              className={"contact" + (recipient === u.username ? " active" : "")}
              onClick={() => onSelect(u.username)}
            >
              <span className="avatar">{u.username[0].toUpperCase()}</span>
              {u.username}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
