import React, { useState, useEffect, useRef } from "react";

function Chat({ backendUrl, isDarkMode }) {
  const chatLogRef = useRef(null);
  const [agentId] = useState(1);
  const [username] = useState("guest");
  const [input, setInput] = useState("");
  const [log, setLog] = useState([]);
  const [loading, setLoading] = useState(false);

  // Helper: simulate streaming chunks with delay
  const streamChunks = async (fullMessage) => {
    const chunkSize = 40; // characters per chunk
    for (let i = 0; i < fullMessage.length; i += chunkSize) {
      const chunk = fullMessage.slice(i, i + chunkSize);
      setLog((l) => [...l, { role: "agent", content: chunk }]);
      
      // Dynamic delay: longer chunks take slightly more time
      const delay = Math.min(Math.max(chunk.length * 25, 300), 1200);
      await new Promise((resolve) => setTimeout(resolve, delay));
    }
  };

  const send = async () => {
    if (!input.trim() || loading) return;
    setLoading(true);

    const messageToSend = input;
    setLog((l) => [...l, { role: "user", content: messageToSend }]);
    setInput("");

    try {
      const res = await fetch(`${backendUrl}/api/chats`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, agent_id: agentId, message: messageToSend }),
      });

      if (!res.ok) throw new Error(`Status ${res.status}`);
      const data = await res.json();

      // Stream response in chunks
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
    if (chatLogRef.current) {
      chatLogRef.current.scrollTop = chatLogRef.current.scrollHeight;
    }
  }, [log, loading]);

  return (
    <div
      style={{
        borderRadius: 12,
        boxShadow: "0 8px 24px rgba(0,0,0,0.15)",
        width: "100%",
        maxWidth: 900,
        display: "flex",
        flexDirection: "column",
        height: "70vh",
        minHeight: 400,
        backgroundColor: isDarkMode ? "rgba(0,0,0,0.6)" : "rgba(255,255,255,0.4)",
        border: isDarkMode ? "1px solid #000" : "1px solid #fff",
      }}
    >
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: 20,
          fontSize: 16,
          display: "flex",
          flexDirection: "column",
          gap: 10,
        }}
        ref={chatLogRef}
      >
        {log.length === 0 && (
          <div
            style={{
              fontStyle: "italic",
              textAlign: "center",
              marginTop: 50,
              fontSize: 24,
              color: isDarkMode ? "#ccc" : "#000",
            }}
          >
            Hey, Let's talk business!, Biashara ni mazungumzo.
          </div>
        )}

        {log.map((m, i) => (
          <div
            key={i}
            style={{
              padding: 12,
              borderRadius: 20,
              maxWidth: "70%",
              wordWrap: "break-word",
              whiteSpace: "pre-wrap",
              boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
              alignSelf: m.role === "user" ? "flex-end" : m.role === "agent" ? "flex-start" : "center",
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
              alignSelf: "flex-start",
              fontStyle: "italic",
              opacity: 0.7,
              backgroundColor: isDarkMode ? "#333" : "#f8f9fa",
              color: isDarkMode ? "#eee" : "#212529",
              padding: 12,
              borderRadius: 20,
              maxWidth: "70%",
              wordWrap: "break-word",
              whiteSpace: "pre-wrap",
            }}
          >
            Kasongo is typing...
          </div>
        )}
      </div>

      <div
        style={{
          padding: 10,
          borderTop: "1px solid",
          borderTopColor: isDarkMode ? "#444" : "#ccc",
          display: "flex",
          alignItems: "center",
          gap: 10,
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
            padding: "10px 20px",
            borderRadius: 40,
            border: "1px solid",
            borderColor: isDarkMode ? "#555" : "#ccc",
            fontSize: 16,
            fontFamily: "inherit",
            minHeight: 40,
            backgroundColor: isDarkMode ? "#333" : "#fff",
            color: isDarkMode ? "#fff" : "#000",
          }}
          rows={2}
          disabled={loading}
        />
        <button
          onClick={send}
          disabled={loading}
          style={{
            backgroundColor: isDarkMode ? "#fff" : "#000",
            color: isDarkMode ? "#000" : "#fff",
            border: "none",
            padding: "10px 24px",
            borderRadius: 24,
            fontWeight: "bold",
            fontSize: 16,
            cursor: loading ? "not-allowed" : "pointer",
            opacity: loading ? 0.6 : 1,
          }}
        >
          {loading ? "Sent" : "Send"}
        </button>
      </div>
    </div>
  );
}

export default Chat;
