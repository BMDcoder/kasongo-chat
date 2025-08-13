import React, { useState, useEffect, useRef } from "react";

const logoUrl = "https://i.postimg.cc/8ktYQrWd/kasongo.png";
const bgImageUrlLight =
  "https://i.postimg.cc/sg19XnLg/kasongo-03.png?auto=format&fit=crop&w=1470&q=80";

// Helper: split message into chunks using punctuation and combine 3 splits per chunk
function splitMessageIntoChunks(message) {
  const splits = message.split(/([.?!])/).filter(Boolean); // keep punctuation
  const chunks = [];
  for (let i = 0; i < splits.length; i += 3) {
    chunks.push(splits.slice(i, i + 3).join("").trim());
  }
  return chunks;
}

// Helper: random delay for human-like typing
function getRandomDelay() {
  return 300 + Math.random() * 700; // 300ms to 1000ms
}

function Chat({ backendUrl, isDarkMode }) {
  const chatLogRef = useRef(null);
  const [agentId] = useState(1);
  const [username] = useState("guest");
  const [input, setInput] = useState("");
  const [log, setLog] = useState([]);
  const [loading, setLoading] = useState(false);
  const [typing, setTyping] = useState(false);

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

      const agentChunks = splitMessageIntoChunks(data.response);
      setTyping(true);

      for (let chunk of agentChunks) {
        await new Promise((resolve) => setTimeout(resolve, getRandomDelay()));
        setLog((l) => [...l, { role: "agent", content: chunk }]);
      }

    } catch (e) {
      console.error(e);
      setLog((l) => [...l, { role: "error", content: "Failed to send message." }]);
    } finally {
      setLoading(false);
      setTyping(false);
    }
  };

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  useEffect(() => {
    if (chatLogRef.current) {
      chatLogRef.current.scrollTop = chatLogRef.current.scrollHeight;
    }
  }, [log, typing]);

  return (
    <div
      style={{
        ...styles.chatContainer,
        backgroundColor: isDarkMode ? "rgba(0,0,0,0.6)" : "rgba(255,255,255,0.4)",
        border: isDarkMode ? "1px solid #000" : "1px solid #fff",
        position: "relative",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <div
        style={{
          ...styles.chatLog,
          overflowY: "auto",
          paddingBottom: 80, // space for floating input
        }}
        ref={chatLogRef}
      >
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
              ...(m.role === "user"
                ? {
                    ...styles.userMsg,
                    alignSelf: "flex-end",
                    backgroundColor: isDarkMode ? "#3a634a" : styles.userMsg.backgroundColor,
                    color: isDarkMode ? "#d1e7dd" : styles.userMsg.color,
                  }
                : m.role === "agent"
                ? {
                    ...styles.agentMsg,
                    alignSelf: "flex-start",
                    backgroundColor: isDarkMode ? "#333" : styles.agentMsg.backgroundColor,
                    color: isDarkMode ? "#eee" : styles.agentMsg.color,
                  }
                : {
                    ...styles.errorMsg,
                    alignSelf: "center",
                    backgroundColor: isDarkMode ? "#722f37" : styles.errorMsg.backgroundColor,
                    color: isDarkMode ? "#f1b0b7" : styles.errorMsg.color,
                  }),
            }}
          >
            {m.content}
          </div>
        ))}

        {typing && (
          <div
            style={{
              ...styles.agentMsg,
              alignSelf: "flex-start",
              fontStyle: "italic",
              display: "flex",
              gap: 4,
              padding: "6px 12px",
              borderRadius: 20,
              backgroundColor: isDarkMode ? "#333" : styles.agentMsg.backgroundColor,
            }}
          >
            <span style={styles.typingDot}></span>
            <span style={styles.typingDot}></span>
            <span style={styles.typingDot}></span>
          </div>
        )}
      </div>

      {/* Floating input box */}
      <div
        style={{
          position: "absolute",
          bottom: 10,
          left: 10,
          right: 10,
          display: "flex",
          gap: 10,
          backgroundColor: isDarkMode ? "#222" : "#fff",
          padding: 10,
          borderRadius: 40,
          boxShadow: "0 4px 10px rgba(0,0,0,0.15)",
        }}
      >
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="How can I help you today..."
          style={{
            flex: 1,
            resize: "none",
            borderRadius: 40,
            border: "1px solid #ccc",
            padding: "10px 20px",
            fontSize: 16,
            backgroundColor: isDarkMode ? "#333" : "#fff",
            color: isDarkMode ? "#eee" : "#000",
          }}
          rows={1}
          disabled={loading}
        />
        <button
          onClick={send}
          style={{
            padding: "10px 24px",
            borderRadius: 24,
            border: "none",
            backgroundColor: isDarkMode ? "#fff" : "#000",
            color: isDarkMode ? "#000" : "#fff",
            cursor: "pointer",
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
    boxShadow: "0 0px 0px rgba(0,0,0,0.0)",
    width: "100%",
    maxWidth: 900,
    display: "flex",
    flexDirection: "column",
    height: "70vh",
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
    padding: "10px 20px",
    borderRadius: 40,
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
  typingDot: {
    width: 8,
    height: 8,
    borderRadius: "50%",
    backgroundColor: "#999",
    animation: "blink 1s infinite",
  },
};
