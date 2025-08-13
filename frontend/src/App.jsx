import React, { useState, useEffect, useRef } from "react";
import { CSSTransition, TransitionGroup } from "react-transition-group";
import "./Chat.css"; // animations here

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
      const chunks = chunkText(data.response, 200); // split bot reply
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

  const chunkText = (text, limit) => {
    const words = text.split(" ");
    const chunks = [];
    let current = "";
    words.forEach((w) => {
      if ((current + w).length > limit) {
        chunks.push(current.trim());
        current = "";
      }
      current += w + " ";
    });
    if (current.trim()) chunks.push(current.trim());
    return chunks;
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

  // Get latest user question for header
  const latestUserMessage = [...log].reverse().find((m) => m.role === "user")?.content || "";

  return (
    <div
      className={`chat-container ${isDarkMode ? "dark" : "light"}`}
      style={{
        backgroundColor: isDarkMode ? "rgba(0,0,0,0.6)" : "rgba(255,255,255,0.4)",
      }}
    >
      {/* HEADER */}
      <div className="chat-header">
        <img src={logoUrl} alt="Kasongo Logo" className="logo" />
        <div className="header-title">{latestUserMessage || "Let's Talk Business"}</div>
      </div>

      {/* MESSAGE LOG */}
      <div className="chat-log" ref={chatLogRef}>
        {log.length === 0 && (
          <div className="placeholder">
            Hey, Let's talk business!, Biashara ni mazungumzo.
          </div>
        )}
        <TransitionGroup component={null}>
          {log.map((m, i) => (
            <CSSTransition key={i} timeout={300} classNames="slide-up">
              <div
                className={`message-block ${m.role}`}
                style={{
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
                }}
              >
                {m.content}
              </div>
            </CSSTransition>
          ))}
        </TransitionGroup>
        {loading && (
          <div className="message-block agent typing">
            Kasongo is typing...
          </div>
        )}
      </div>

      {/* INPUT FOOTER */}
      <div className="chat-input-footer">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="How can I help you today..."
          disabled={loading}
        />
        <button onClick={send} disabled={loading}>
          {loading ? "Sent" : "Send"}
        </button>
      </div>
    </div>
  );
}

export default function App() {
  const backendUrl = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";
  const [isDarkMode, setIsDarkMode] = useState(false);

  return (
    <div
      className="app-container"
      style={{
        backgroundImage: `url(${bgImageUrlLight})`,
        color: isDarkMode ? "#eee" : "#333",
      }}
    >
      <Chat backendUrl={backendUrl} isDarkMode={isDarkMode} />
      <footer className="app-footer">
        <button onClick={() => setIsDarkMode((d) => !d)}>
          {isDarkMode ? "Light Mode" : "Dark Mode"}
        </button>
        <div>
          powered by{" "}
          <a
            href="https://bmdigital.netlify.app"
            target="_blank"
            rel="noopener noreferrer"
          >
            BMDigital
          </a>
        </div>
      </footer>
    </div>
  );
}
