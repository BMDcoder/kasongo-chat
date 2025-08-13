import React, { useState, useEffect, useRef } from "react";

const logoUrl = "https://i.postimg.cc/8ktYQrWd/kasongo.png";
const bgImageUrlLight =
  "https://i.postimg.cc/sg19XnLg/kasongo-03.png?auto=format&fit=crop&w=1470&q=80";

function Chat({ backendUrl, isDarkMode }) {
  const chatLogRef = useRef(null);
  const [agentId] = useState(1);
  const [username] = useState("guest");
  const [input, setInput] = useState("");
  const [log, setLog] = useState([]);
  const [loading, setLoading] = useState(false);
  const [typingDots, setTypingDots] = useState("");

  // Animate typing dots
  useEffect(() => {
    if (!loading) {
      setTypingDots("");
      return;
    }
    const interval = setInterval(() => {
      setTypingDots((prev) => (prev.length < 3 ? prev + "." : ""));
    }, 500);
    return () => clearInterval(interval);
  }, [loading]);

 // Split text by punctuation but combine every 3 pieces
const splitMessage = (text) => {
  const regex = /[^.!?]+[.!?]?/g;
  const parts = text.match(regex) || [text];

  const combinedChunks = [];
  for (let i = 0; i < parts.length; i += 3) {
    const chunk = parts.slice(i, i + 3).join(" ").trim();
    if (chunk) combinedChunks.push(chunk);
  }
  return combinedChunks;
};

// Streaming chunks with dynamic delay
const streamChunks = async (message) => {
  const chunks = splitMessage(message);
  for (const chunk of chunks) {
    setLog((l) => [...l, { role: "agent", content: chunk }]);
    const delay = Math.min(Math.max(chunk.length * 40, 300), 2000); // dynamic delay
    await new Promise((resolve) => setTimeout(resolve, delay));
  }
};

  const send = async () => {
    if (!input.trim() || loading) return;
    setLoading(true);

    const userMessage = input;
    setLog((l) => [...l, { role: "user", content: userMessage }]);
    setInput("");

    try {
      const res = await fetch(`${backendUrl}/api/chats`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, agent_id: agentId, message: userMessage }),
      });
      if (!res.ok) throw new Error(`Status ${res.status}`);
      const data = await res.json();
      await streamChunks(data.response);
    } catch (e) {
      setLog((l) => [...l, { role: "error", content: "Failed to send message." }]);
      console.error("Chat request failed:", e);
    } finally {
      setLoading(false);
    }
  };

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  useEffect(() => {
    if (chatLogRef.current) chatLogRef.current.scrollTop = chatLogRef.current.scrollHeight;
  }, [log, loading]);

  return (
    <div
      style={{
        ...styles.chatContainer,
        backgroundColor: isDarkMode ? "rgba(0,0,0,0.6)" : "rgba(255,255,255,0.4)",
        border: isDarkMode ? "1px solid #000" : "1px solid #fff",
      }}
    >
      <div style={styles.chatLog} ref={chatLogRef}>
        {log.length === 0 && (
          <div style={{ ...styles.placeholder, color: isDarkMode ? "#ccc" : "#000" }}>
            Hey, Let's talk business!, Biashara ni mazungumzo.
          </div>
        )}

        {log.map((m, i) => (
          <div
            key={i}
            style={{
              ...styles.message,
              alignSelf:
                m.role === "user" ? "flex-end" : m.role === "agent" ? "flex-start" : "center",
              backgroundColor:
                m.role === "user"
                  ? isDarkMode
                    ? "#3a634a"
                    : styles.userMsg.backgroundColor
                  : m.role === "agent"
                  ? isDarkMode
                    ? "#333"
                    : styles.agentMsg.backgroundColor
                  : isDarkMode
                  ? "#722f37"
                  : styles.errorMsg.backgroundColor,
              color:
                m.role === "user"
                  ? isDarkMode
                    ? "#d1e7dd"
                    : styles.userMsg.color
                  : m.role === "agent"
                  ? isDarkMode
                    ? "#eee"
                    : styles.agentMsg.color
                  : isDarkMode
                  ? "#f1b0b7"
                  : styles.errorMsg.color,
            }}
          >
            {m.content}
          </div>
        ))}

        {loading && (
          <div
            style={{
              ...styles.agentMsg,
              alignSelf: "flex-start",
              fontStyle: "italic",
              opacity: 0.8,
              display: "flex",
              gap: 4,
              backgroundColor: isDarkMode ? "#333" : styles.agentMsg.backgroundColor,
              color: isDarkMode ? "#eee" : styles.agentMsg.color,
            }}
          >
            <span>Kasongo</span>
            <span>{typingDots}</span>
          </div>
        )}
      </div>

      {/* Floating input box */}
      <div
        style={{
          ...styles.floatingInputContainer,
          backgroundColor: isDarkMode ? "#222" : "#fff",
          borderColor: isDarkMode ? "#555" : "#ccc",
        }}
      >
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Type a message..."
          style={{
            ...styles.floatingTextarea,
            backgroundColor: isDarkMode ? "#333" : "#f9f9f9",
            color: isDarkMode ? "#fff" : "#000",
            borderColor: isDarkMode ? "#555" : "#ccc",
          }}
          rows={1}
          disabled={loading}
        />
        <button
          onClick={send}
          style={{
            ...styles.sendButton,
            backgroundColor: isDarkMode ? "#fff" : "#000",
            color: isDarkMode ? "#000" : "#fff",
            cursor: loading ? "not-allowed" : "pointer",
            opacity: loading ? 0.6 : 1,
          }}
          disabled={loading}
        >
          Send
        </button>
      </div>
    </div>
  );
}

export default function App() {
  const backendUrl = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";
  const [isDarkMode, setIsDarkMode] = useState(false);

  const toggleDarkMode = () => setIsDarkMode((d) => !d);

  return (
    <div
      style={{
        ...styles.appContainer,
        backgroundImage: `url(${bgImageUrlLight})`,
        color: isDarkMode ? "#eee" : "#333",
      }}
    >
      <div
        style={{
          ...styles.overlay,
          backgroundColor: isDarkMode ? "rgba(0,0,0,0.5)" : "rgba(255,255,255,0.2)",
        }}
      />
      <header style={styles.header}>
        <img src={logoUrl} alt="Kasongo Logo" style={styles.logo} />
      </header>
      <main style={styles.main}>
        <Chat backendUrl={backendUrl} isDarkMode={isDarkMode} />
      </main>
      <footer
        style={{
          ...styles.footer,
          backgroundColor: "rgba(255,255,255,0.6)",
          color: "#555",
          position: "relative",
        }}
      >
        <button
          onClick={toggleDarkMode}
          style={{
            padding: "6px 12px",
            borderRadius: 20,
            border: "none",
            cursor: "pointer",
            backgroundColor: isDarkMode ? "#555" : "#ddd",
            color: isDarkMode ? "#eee" : "#333",
            fontWeight: "bold",
            position: "absolute",
            left: 12,
            bottom: 12,
            userSelect: "none",
          }}
          aria-label="Toggle light/dark mode"
          title="Toggle light/dark mode"
        >
          {isDarkMode ? "Light Mode" : "Dark Mode"}
        </button>
        <div>
          powered by{" "}
          <a
            href="https://bmdigital.netlify.app"
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: "#555", textDecoration: "underline" }}
          >
            BMDigital
          </a>
        </div>
      </footer>
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
    zIndex: 0,
  },
  header: {
    position: "relative",
    zIndex: 1,
    padding: "20px 0",
    textAlign: "center",
    backgroundColor: "rgba(255,255,255,0.6)",
    boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
  },
  logo: {
    height: 40,
    objectFit: "contain",
  },
  main: {
    flex: 1,
    position: "relative",
    zIndex: 1,
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    padding: 5,
  },
  chatContainer: {
    borderRadius: 12,
    boxShadow: "0 8px 24px rgba(0,0,0,0.15)",
    width: "100%",
    maxWidth: 900,
    display: "flex",
    flexDirection: "column",
    height: "70vh",
    minHeight: 400,
    position: "relative",
    paddingBottom: 60, // space for floating input
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
    fontStyle: "italic",
    textAlign: "center",
    marginTop: 50,
    fontSize: 24,
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
  floatingInputContainer: {
    position: "absolute",
    bottom: 10,
    left: 10,
    right: 10,
    display: "flex",
    gap: 10,
    padding: 10,
    borderRadius: 30,
    border: "1px solid #ccc",
    boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
  },
  floatingTextarea: {
    flex: 1,
    resize: "none",
    padding: "10px 20px",
    borderRadius: 30,
    border: "1px solid #ccc",
    fontSize: 16,
    fontFamily: "inherit",
    minHeight: 40,
  },
  sendButton: {
    backgroundColor: "#000000",
    border: "none",
    padding: "10px 24px",
    borderRadius: 24,
    fontWeight: "bold",
    fontSize: 16,
    userSelect: "none",
  },
  footer: {
    position: "relative",
    zIndex: 1,
    textAlign: "center",
    padding: "16px 8px",
    fontSize: 14,
    boxShadow: "0 -2px 8px rgba(0,0,0,0.1)",
  },
};
