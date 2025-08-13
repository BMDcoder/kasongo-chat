import React, { useState, useEffect, useRef } from "react";

const logoUrl = "https://i.postimg.cc/8ktYQrWd/kasongo.png";

function Chat({ backendUrl, isDarkMode }) {
  const chatLogRef = useRef(null);
  const [agentId] = useState(1);
  const [username] = useState("guest");
  const [input, setInput] = useState("");
  const [log, setLog] = useState([]);
  const [loading, setLoading] = useState(false);

  // Splits long text into short "paragraph card" chunks
  const chunkText = (text, maxSentences = 2) => {
    const sentences = text.split(/(?<=[.?!])\s+/);
    const chunks = [];
    for (let i = 0; i < sentences.length; i += maxSentences) {
      chunks.push(sentences.slice(i, i + maxSentences).join(" "));
    }
    return chunks;
  };

  const send = async () => {
    if (!input.trim() || loading) return;
    setLoading(true);
    const body = { username, agent_id: agentId, message: input };
    try {
      const res = await fetch(`${backendUrl}/api/chats`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`Status ${res.status}`);
      const data = await res.json();
      const chunks = chunkText(data.response);

      setLog((l) => [
        ...l,
        { role: "user", content: input },
        ...chunks.map((c) => ({ role: "agent", content: c })),
      ]);
      setInput("");
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
    if (chatLogRef.current) {
      chatLogRef.current.scrollTop = chatLogRef.current.scrollHeight;
    }
  }, [log, loading]);

  // Create a short summary title from last user message
  const lastUserMessage = [...log].reverse().find((m) => m.role === "user")?.content || "";
  const summaryTitle =
    lastUserMessage.length > 30
      ? lastUserMessage.substring(0, 27) + "..."
      : lastUserMessage || "Kasongo AI";

  return (
    <div
      style={{
        ...styles.chatContainer,
        backgroundColor: isDarkMode ? "#1a1a1a" : "#fff",
        border: isDarkMode ? "1px solid #000" : "1px solid #ddd",
      }}
    >
      {/* Header */}
      <div style={{ ...styles.headerBar, backgroundColor: isDarkMode ? "#222" : "#f9f9f9" }}>
        <img src={logoUrl} alt="Kasongo Logo" style={styles.logo} />
        <div style={styles.headerTitle}>{summaryTitle}</div>
        <div style={styles.headerSpacer}></div>
      </div>

      {/* Content */}
      <div style={styles.chatLog} ref={chatLogRef}>
        {log.length === 0 && (
          <div style={{ ...styles.placeholder, color: isDarkMode ? "#ccc" : "#000" }}>
            Hey, Let's talk business! Biashara ni mazungumzo.
          </div>
        )}

        {log.map((m, i) => (
          <div
            key={i}
            style={{
              ...styles.messageBlock,
              ...(m.role === "user"
                ? styles.userBlock
                : m.role === "agent"
                ? styles.agentBlock
                : styles.errorBlock),
              backgroundColor:
                m.role === "user"
                  ? isDarkMode
                    ? "#3a634a"
                    : "#d1e7dd"
                  : m.role === "agent"
                  ? isDarkMode
                    ? "#333"
                    : "#f8f9fa"
                  : isDarkMode
                  ? "#722f37"
                  : "#f8d7da",
              color:
                m.role === "user"
                  ? isDarkMode
                    ? "#d1e7dd"
                    : "#0f5132"
                  : m.role === "agent"
                  ? isDarkMode
                    ? "#eee"
                    : "#212529"
                  : isDarkMode
                  ? "#f1b0b7"
                  : "#842029",
            }}
          >
            {m.content}
          </div>
        ))}

        {loading && (
          <div
            style={{
              ...styles.messageBlock,
              ...styles.agentBlock,
              fontStyle: "italic",
              opacity: 0.7,
              backgroundColor: isDarkMode ? "#333" : "#f8f9fa",
              color: isDarkMode ? "#eee" : "#212529",
            }}
          >
            Kasongo is typing...
          </div>
        )}
      </div>

      {/* Footer */}
      <div style={{ ...styles.inputContainer, backgroundColor: isDarkMode ? "#222" : "#f9f9f9" }}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Type your message..."
          style={{
            ...styles.textarea,
            backgroundColor: isDarkMode ? "#333" : "#fff",
            color: isDarkMode ? "#fff" : "#000",
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
            opacity: loading ? 0.6 : 1,
          }}
          disabled={loading}
        >
          {loading ? "Sending..." : "Send"}
        </button>
      </div>
    </div>
  );
}

const styles = {
  chatContainer: {
    display: "flex",
    flexDirection: "column",
    height: "70vh",
    borderRadius: 12,
    overflow: "hidden",
    boxShadow: "0 8px 24px rgba(0,0,0,0.15)",
  },
  headerBar: {
    display: "flex",
    alignItems: "center",
    padding: "10px 15px",
    borderBottom: "1px solid #ccc",
  },
  logo: { height: 28, marginRight: 10 },
  headerTitle: { flex: 1, fontWeight: "bold", fontSize: 16 },
  headerSpacer: { width: 28 },
  chatLog: {
    flex: 1,
    padding: 20,
    display: "flex",
    flexDirection: "column",
    gap: 10,
    overflowY: "auto",
  },
  placeholder: {
    fontStyle: "italic",
    textAlign: "center",
    fontSize: 18,
  },
  messageBlock: {
    padding: 12,
    borderRadius: 10,
    maxWidth: "80%",
    lineHeight: 1.4,
  },
  userBlock: { alignSelf: "flex-end" },
  agentBlock: { alignSelf: "flex-start" },
  errorBlock: { alignSelf: "center" },
  inputContainer: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "8px 10px",
    borderTop: "1px solid #ccc",
  },
  textarea: {
    flex: 1,
    resize: "none",
    borderRadius: 20,
    padding: "8px 12px",
    border: "1px solid #ccc",
    fontSize: 14,
    fontFamily: "inherit",
  },
  sendButton: {
    border: "none",
    borderRadius: 20,
    padding: "8px 16px",
    fontWeight: "bold",
    cursor: "pointer",
  },
};

export default Chat;
