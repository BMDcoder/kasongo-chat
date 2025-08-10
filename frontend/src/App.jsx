import React, { useState } from "react";

const logoUrl = "https://yourdomain.com/logo.png"; // <-- Replace with your actual logo URL
const bgImageUrl = "https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=1470&q=80"; // example background image

function Chat({ backendUrl }) {
  const [agentId] = useState(1); // fixed to 1 since no UI to change
  const [username] = useState("guest"); // fixed to guest, no UI input
  const [input, setInput] = useState("");
  const [log, setLog] = useState([]);

  const send = async () => {
    if (!input.trim()) return;
    const body = { username, agent_id: agentId, message: input };
    try {
      const res = await fetch(`${backendUrl}/api/chats`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`Status ${res.status}`);
      const data = await res.json();
      setLog((l) => [...l, { role: "user", content: input }, { role: "agent", content: data.response }]);
      setInput("");
    } catch (e) {
      setLog((l) => [...l, { role: "error", content: "Failed to send message." }]);
      console.error("Chat request failed:", e);
    }
  };

  // Send on Enter key press
  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div style={styles.chatContainer}>
      <div style={styles.chatLog}>
        {log.length === 0 && <div style={styles.placeholder}>Say hi to your AI agent!</div>}
        {log.map((m, i) => (
          <div
            key={i}
            style={{
              ...styles.message,
              ...(m.role === "user" ? styles.userMsg : m.role === "agent" ? styles.agentMsg : styles.errorMsg),
            }}
          >
            <strong>{m.role === "user" ? "You" : m.role === "agent" ? "Agent" : "Error"}:</strong> {m.content}
          </div>
        ))}
      </div>
      <div style={styles.inputContainer}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Type your message..."
          style={styles.textarea}
          rows={2}
        />
        <button onClick={send} style={styles.sendButton}>
          Send
        </button>
      </div>
    </div>
  );
}

export default function App() {
  const backendUrl = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

  return (
    <div style={{ ...styles.appContainer, backgroundImage: `url(${bgImageUrl})` }}>
      <div style={styles.overlay} />
      <header style={styles.header}>
        <img src={logoUrl} alt="Logo" style={styles.logo} />
      </header>
      <main style={styles.main}>
        <Chat backendUrl={backendUrl} />
      </main>
      <footer style={styles.footer}>powered by BMDigital</footer>
    </div>
  );
}

const styles = {
  appContainer: {
    position: "relative",
    minHeight: "100vh",
    backgroundSize: "cover",
    backgroundPosition: "center",
    fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
    color: "#333",
    display: "flex",
    flexDirection: "column",
  },
  overlay: {
    position: "fixed",
    top: 0, left: 0, right: 0, bottom: 0,
    backdropFilter: "blur(8px)",
    backgroundColor: "rgba(255,255,255,0.2)",
    zIndex: 0,
  },
  header: {
    position: "relative",
    zIndex: 1,
    padding: "20px 0",
    textAlign: "center",
    backgroundColor: "rgba(255,255,255,0.6)",
    boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
  },
  logo: {
    height: 60,
    objectFit: "contain",
  },
  main: {
    flex: 1,
    position: "relative",
    zIndex: 1,
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    padding: 20,
  },
  chatContainer: {
    backgroundColor: "rgba(255,255,255,0.85)",
    borderRadius: 12,
    boxShadow: "0 8px 24px rgba(0,0,0,0.15)",
    width: "100%",
    maxWidth: 600,
    display: "flex",
    flexDirection: "column",
    height: "80vh",
  },
  chatLog: {
    flex: 1,
    overflowY: "auto",
    padding: 20,
    fontSize: 16,
  },
  placeholder: {
    color: "#888",
    fontStyle: "italic",
    textAlign: "center",
    marginTop: 50,
  },
  message: {
    marginBottom: 12,
    padding: 10,
    borderRadius: 8,
  },
  userMsg: {
    backgroundColor: "#d1e7dd",
    alignSelf: "flex-end",
    maxWidth: "80%",
  },
  agentMsg: {
    backgroundColor: "#f8d7da",
    alignSelf: "flex-start",
    maxWidth: "80%",
  },
  errorMsg: {
    backgroundColor: "#f5c6cb",
    color: "#721c24",
    alignSelf: "center",
    maxWidth: "80%",
  },
  inputContainer: {
    padding: 10,
    borderTop: "1px solid #ccc",
    display: "flex",
    alignItems: "center",
    gap: 10,
  },
  textarea: {
    flex: 1,
    resize: "none",
    padding: 10,
    borderRadius: 8,
    border: "1px solid #ccc",
    fontSize: 16,
    fontFamily: "inherit",
  },
  sendButton: {
    backgroundColor: "#007bff",
    border: "none",
    color: "white",
    padding: "10px 18px",
    borderRadius: 8,
    cursor: "pointer",
    fontWeight: "bold",
    fontSize: 16,
  },
  footer: {
    position: "relative",
    zIndex: 1,
    textAlign: "center",
    padding: 12,
    fontSize: 14,
    color: "#555",
    backgroundColor: "rgba(255,255,255,0.6)",
    boxShadow: "0 -2px 8px rgba(0,0,0,0.1)",
  },
};
