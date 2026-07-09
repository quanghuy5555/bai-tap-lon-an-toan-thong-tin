// api.js — lớp gọi REST tới backend FastAPI.
const BASE = "http://localhost:8000";

async function j(method, path, body) {
  const res = await fetch(BASE + path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = data.detail || `Lỗi HTTP ${res.status}`;
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return data;
}

export const api = {
  // Users
  createUser: (username) => j("POST", "/users", { username }),
  listUsers: () => j("GET", "/users"),

  // Messages
  sendMessage: (sender, recipient, audio_base64) =>
    j("POST", "/messages", { sender, recipient, audio_base64 }),
  inbox: (username) => j("GET", `/messages/${encodeURIComponent(username)}`),
  decrypt: (id) => j("POST", `/messages/${id}/decrypt`),
  raw: (id) => j("GET", `/messages/${id}/raw`),
  attack: (id, field) => j("POST", `/messages/${id}/attack?field=${field}`),
};
