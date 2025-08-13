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

  // Scroll chat to bottom on new messages or loading change
  useEffect(() => {
    if (chatLogRef.current) {
      chatLogRef.current.scrollTop = chatLogRef.current.scrollHeight;
    }
  }, [log, loading]);

  // Send message to backend API
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

      // Add user message
      setLog((l) => [...l, { role: "user", content: input }]);
      setInput("");

      // Split agent response by sentences and display sequentially
      const chunks = data.response
        .split(/(?<=[.!?])\s+/)
        .filter(Boolean);

      for (let i = 0; i < chunks.length; i++) {
        await new Promise((r) => setTimeout(r, i === 0 ? 300 : 600));
        setLog((l) => [...l, { role: "agent", content: chunks[i] }]);
      }
    } catch (error) {
      setLog((l) => [...l, { role: "error", content: "Failed to send message." }]);
      console.error("Chat request failed:", error);
    } finally {
      setLoading(false);
    }
  };

  // Handle Enter key (send) with Shift+Enter for new line
  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  // Get latest user message for header display
  const latestUserMsg = [...log].reverse().find((m) => m.role === "user")?.content || "Let's talk business!";
  const headerTitle = latestUserMsg.length > 40 ? latestUserMsg.slice(0, 37) + "..." : latestUserMsg;

  return (
    <div
      style={{
        ...styles.chatContainer,
        backgroundColor: isDarkMode ? "rgba(10,10,10,0.75)" : "rgba(255,255,255,0.75)",
        border: isDarkMode ? "1px solid #111" : "1px solid #ddd",
        color: isDarkMode ? "#eee" : "#111",
        display: "flex",
        flexDirection: "column",
        height: "70vh",
        maxWidth: 900,
        borderRadius: 16,
        boxShadow: "0 8px 32px rgba(0,0,0,0.15)",
        overflow: "hidden",
      }}
    >
      {/* Chat Header */}
      <div
        style={{
          backgroundColor: isDarkMode ? "#16213e" : "#2563eb",
          color: "white",
          padding: "12px 20px",
          fontWeight: "600",
          fontSize: 18,
          display: "flex",
          alignItems: "center",
          gap: 16,
          userSelect: "none",
        }}
      >
        <img
          src={logoUrl}
          alt="Kasongo Logo"
          style={{ height: 30, objectFit: "contain", filter: isDarkMode ? "brightness(0) invert(1)" : "none" }}
        />
        <div
          title={latestUserMsg}
          style={{
            flex: 1,
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
            fontStyle: "italic",
          }}
        >
          {headerTitle}
        </div>
      </div>

      {/* Chat Messages */}
      <div
        ref={chatLogRef}
        style={{
          flex: 1,
          overflowY: "auto",
          padding: 20,
          display: "flex",
          flexDirection: "column",
          gap: 12,
          background: isDarkMode ? "rgba(0,0,0,0.5)" : "rgba(240, 248, 255, 0.8)",
          backdropFilter: "blur(10px)",
        }}
      >
        {log.length === 0 && (
          <div
            style={{
              fontStyle: "italic",
              fontSize: 22,
              textAlign: "center",
              marginTop: 60,
              color: isDarkMode ? "#aaa" : "#444",
            }}
          >
            Hey, Let's talk business!, Biashara ni mazungumzo.
          </div>
        )}
        {log.map((msg, idx) => {
          const isUser = msg.role === "user";
          const isAgent = msg.role === "agent";
          const isError = msg.role === "error";
          return (
            <div
              key={idx}
              style={{
                alignSelf: isUser ? "flex-end" : isAgent ? "flex-start" : "center",
                backgroundColor: isUser
                  ? isDarkMode
                    ? "#1e3a8a"
                    : "#3b82f6"
                  : isAgent
                  ? isDarkMode
                    ? "#1f2937"
                    : "#e2e8f0"
                  : isDarkMode
                  ? "#6b2121"
                  : "#f87171",
                color: isUser ? "#dbeafe" : isAgent ? (isDarkMode ? "#d1d5db" : "#1f2937") : "#fee2e2",
                padding: "14px 20px",
                borderRadius: 20,
                maxWidth: "75%",
                fontSize: 16,
                lineHeight: 1.5,
                whiteSpace: "pre-wrap",
                boxShadow: "0 2px 8px rgb(0 0 0 / 0.12)",
                userSelect: "text",
              }}
            >
              {msg.content}
            </div>
          );
        })}
        {loading && (
          <div
            style={{
              alignSelf: "flex-start",
              fontStyle: "italic",
              opacity: 0.75,
              color: isDarkMode ? "#cbd5e1" : "#374151",
              paddingLeft: 10,
              userSelect: "none",
            }}
          >
            Kasongo is typing<span style={{ animation: "blink 1.5s step-start 0s infinite" }}>...</span>
          </div>
        )}
      </div>

      {/* Input Area */}
      <div
        style={{
          borderTop: `1px solid ${isDarkMode ? "#333" : "#ddd"}`,
          backgroundColor: isDarkMode ? "#0f172a" : "#f9fafb",
          padding: 16,
          display: "flex",
          gap: 10,
          alignItems: "center",
          position: "sticky",
          bottom: 0,
          zIndex: 10,
        }}
      >
        <textarea
          rows={2}
          placeholder="How can I help you today..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={loading}
          style={{
            flex: 1,
            padding: "12px 16px",
            borderRadius: 24,
            border: `1px solid ${isDarkMode ? "#334155" : "#cbd5e1"}`,
            backgroundColor: isDarkMode ? "#1e293b" : "white",
            color: isDarkMode ? "white" : "#111827",
            fontSize: 16,
            resize: "none",
            outline: "none",
            fontFamily: "inherit",
            boxShadow: "0 1px 3px rgb(0 0 0 / 0.1)",
            transition: "border-color 0.3s",
          }}
          onFocus={(e) => (e.target.style.borderColor = "#2563eb")}
          onBlur={(e) => (e.target.style.borderColor = isDarkMode ? "#334155" : "#cbd5e1")}
        />
        <button
          onClick={send}
          disabled={loading}
          style={{
            backgroundColor: isDarkMode ? "#2563eb" : "#1e40af",
            color: "white",
            fontWeight: "600",
            fontSize: 16,
            padding: "12px 24px",
            borderRadius: 24,
            border: "none",
            cursor: loading ? "not-allowed" : "pointer",
            opacity: loading ? 0.6 : 1,
            boxShadow: "0 4px 10px rgb(37 99 235 / 0.5)",
            userSelect: "none",
            transition: "background-color 0.3s",
          }}
          onMouseEnter={(e) => !loading && (e.currentTarget.style.backgroundColor = "#1e40af")}
          onMouseLeave={(e) => !loading && (e.currentTarget.style.backgroundColor = isDarkMode ? "#2563eb" : "#1e40af")}
        >
          {loading ? "Sending..." : "Send"}
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
        position: "relative",
        minHeight: "100vh",
        fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
        backgroundImage: `url(${bgImageUrlLight})`,
        backgroundSize: "cover",
        backgroundPosition: "center",
        color: isDarkMode ? "#e0e7ff" : "#1e293b",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* Background Overlay */}
      <div
        style={{
          position: "fixed",
          inset: 0,
          backdropFilter: "blur(8px)",
          backgroundColor: isDarkMode ? "rgba(0,0,0,0.5)" : "rgba(255,255,255,0.3)",
          zIndex: 0,
        }}
      />
      {/* Header */}
      <header
        style={{
          position: "relative",
          zIndex: 1,
          padding: "24px 0",
          textAlign: "center",
          backgroundColor: isDarkMode ? "rgba(22, 25, 35, 0.85)" : "rgba(37, 99, 235, 0.85)",
          boxShadow: isDarkMode
            ? "0 4px 10px rgba(0,0,0,0.6)"
            : "0 4px 12px rgba(37, 99, 235, 0.4)",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          gap: 12,
          userSelect: "none",
          fontWeight: "700",
          fontSize: 22,
          color: "white",
          letterSpacing: 1,
          textShadow: "0 0 6px rgba(0,0,0,0.2)",
          cursor: "default",
          zIndex: 2,
        }}
      >
        <img
          src={logoUrl}
          alt="Kasongo Logo"
          style={{ height: 44, objectFit: "contain" }}
        />
        Kasongo Chat
      </header>

      {/* Main Chat */}
      <main
        style={{
          flex: 1,
          position: "relative",
          zIndex: 1,
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          padding: 12,
        }}
      >
        <Chat backendUrl={backendUrl} isDarkMode={isDarkMode} />
      </main>

      {/* Footer */}
      <footer
        style={{
          position: "relative",
          zIndex: 1,
          padding: "16px 8px",
          fontSize: 14,
          textAlign: "center",
          backgroundColor: isDarkMode ? "rgba(22, 25, 35, 0.8)" : "rgba(255,255,255,0.85)",
          color: isDarkMode ? "#94a3b8" : "#444",
          userSelect: "none",
          boxShadow: "0 -4px 10px rgba(0,0,0,0.1)",
        }}
      >
        <button
          onClick={toggleDarkMode}
          style={{
            padding: "6px 14px",
            borderRadius: 24,
            border: "none",
            cursor: "pointer",
            backgroundColor: isDarkMode ? "#475569" : "#e2e8f0",
            color: isDarkMode ? "#cbd5e1" : "#1e293b",
            fontWeight: "600",
            marginBottom: 8,
            userSelect: "none",
            transition: "background-color 0.3s",
          }}
          aria-label="Toggle light/dark mode"
          title="Toggle light/dark mode"
          onMouseEnter={(e) =>
            (e.currentTarget.style.backgroundColor = isDarkMode ? "#64748b" : "#cbd5e1")
          }
          onMouseLeave={(e) =>
            (e.currentTarget.style.backgroundColor = isDarkMode ? "#475569" : "#e2e8f0")
          }
        >
          {isDarkMode ? "Light Mode" : "Dark Mode"}
        </button>
        <div>
          powered by{" "}
          <a
            href="https://bmdigital.netlify.app"
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: isDarkMode ? "#94a3b8" : "#444", textDecoration: "underline" }}
          >
            BMDigital
          </a>
        </div>
      </footer>

      <style>{`
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0; }
        }
      `}</style>
    </div>
  );
}

const styles = {
  chatContainer: {
    boxSizing: "border-box",
  },
};
