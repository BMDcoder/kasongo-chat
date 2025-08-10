import React, { useState } from "react";

const logoUrl = "https://i.postimg.cc/8ktYQrWd/kasongo.png";
const bgImageUrl = "https://i.postimg.cc/8z2KB2fs/kasongobg-03.png?auto=format&fit=crop&w=1470&q=80";

function Chat({ backendUrl }) {
  const [agentId] = useState(1);
  const [username] = useState("guest");
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

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div style={styles.chatContainer}>
      <div style={styles.chatLog}>
        {log.length === 0 && <div style={styles.placeholder}>Hey, Let's talk business!</div>}
        {log.map((m, i) => (
          <div
            key={i}
            style={{
              ...styles.message,
              ...(m.role === "user"
                ? { ...styles.userMsg, alignSelf: "flex-end" }
                : m.role === "agent"
                ? { ...styles.agentMsg, alignSelf: "flex-start" }
                : { ...styles.errorMsg, alignSelf: "center" }),
            }}
          >
            {m.content}
          </div>
        ))}
      </div>
      <div style={styles.inputContainer}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="How can I help you today..."
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
        <img src={logoUrl} alt="Kasongo Logo" style={styles.logo} />
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
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
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
    width: "80%",
    maxWidth: 'none',
    display: "flex",
    flexDirection: "column",
    height: "80vh",
    minHeight: 400,
  },
  chatLog: {
    flex: 1,
    overflowY: "auto",
    padding: 20,
    fontSize: 16,
    display: "flex",
    flexDirection: "column",
    gap: 10,
  },
  placeholder: {
    color: "#888",
    fontStyle: "italic",
    textAlign: "center",
    marginTop: 50,
  },
  message: {
    padding: 12,
    borderRadius: 20,
    maxWidth: "70%",
    wordWrap: "break-word",
    whiteSpace: "pre-wrap",
    boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
  },
  userMsg: {
    backgroundColor: "#d1e7dd",
    color: "#0f5132",
  },
  agentMsg: {
    backgroundColor: "#f8f9fa",
    color: "#212529",
  },
  errorMsg: {
    backgroundColor: "#f8d7da",
    color: "#842029",
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
    borderRadius: 12,
    border: "1px solid #ccc",
    fontSize: 16,
    fontFamily: "inherit",
    minHeight: 40,
  },
  sendButton: {
    backgroundColor: "#000000",
    border: "none",
    color: "white",
    padding: "10px 24px",
    borderRadius: 24,
    cursor: "pointer",
    fontWeight: "bold",
    fontSize: 16,
    userSelect: "none",
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
