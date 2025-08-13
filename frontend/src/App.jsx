import React, { useState, useEffect, useRef } from "react";

export default function ChatPage() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const messagesEndRef = useRef(null);

  // Scroll to latest
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Handle sending message (unchanged backend action)
  const sendMessage = async () => {
    if (!input.trim()) return;
    const userMessage = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);

    setInput("");

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: input }),
      });
      const data = await res.json();
      if (data.reply) {
        // chunk answer into sentences
        const chunks = data.reply
          .split(/(?<=[.!?])\s+/)
          .map((chunk) => chunk.trim())
          .filter((chunk) => chunk);
        chunks.forEach((chunk, i) => {
          setTimeout(() => {
            setMessages((prev) => [
              ...prev,
              { role: "assistant", content: chunk },
            ]);
          }, i * 800); // delay between chunks
        });
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Extract last user question for header summary
  const latestUserQuestion =
    [...messages]
      .reverse()
      .find((m) => m.role === "user")?.content || "Ask me anything";

  const shortHeaderTitle =
    latestUserQuestion.length > 40
      ? latestUserQuestion.slice(0, 37) + "..."
      : latestUserQuestion;

  return (
    <div
      style={{
        height: "100vh",
        display: "flex",
        flexDirection: "column",
        fontFamily: "Arial, sans-serif",
        backgroundColor: "#f9f9f9",
      }}
    >
      {/* Header */}
      <div
        style={{
          backgroundColor: "#1e293b",
          color: "white",
          padding: "12px 16px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          position: "sticky",
          top: 0,
          zIndex: 2,
        }}
      >
        <div style={{ fontWeight: "bold", fontSize: "16px" }}>MyLogo</div>
        <div
          style={{
            fontSize: "14px",
            fontStyle: "italic",
            textAlign: "center",
            flex: 1,
            padding: "0 10px",
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          {shortHeaderTitle}
        </div>
      </div>

      {/* Messages */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "10px 16px",
          marginBottom: "70px", // leave space for footer
        }}
      >
        {messages.map((msg, i) => (
          <div
            key={i}
            style={{
              display: "flex",
              justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
              marginBottom: "8px",
            }}
          >
            <div
              style={{
                backgroundColor:
                  msg.role === "user" ? "#3b82f6" : "#e2e8f0",
                color: msg.role === "user" ? "white" : "#111827",
                padding: "8px 12px",
                borderRadius: "10px",
                maxWidth: "75%",
                boxShadow:
                  "0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06)",
                fontSize: "14px",
                lineHeight: "1.4",
                whiteSpace: "pre-wrap",
              }}
            >
              {msg.content}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Footer Input */}
      <div
        style={{
          position: "fixed",
          bottom: 0,
          left: 0,
          right: 0,
          backgroundColor: "#ffffff",
          padding: "10px 16px",
          borderTop: "1px solid #e5e7eb",
          display: "flex",
          alignItems: "center",
          gap: "8px",
        }}
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
          placeholder="Type your message..."
          style={{
            flex: 1,
            padding: "8px 12px",
            borderRadius: "8px",
            border: "1px solid #d1d5db",
            outline: "none",
            fontSize: "14px",
          }}
        />
        <button
          onClick={sendMessage}
          style={{
            backgroundColor: "#3b82f6",
            color: "white",
            border: "none",
            borderRadius: "8px",
            padding: "8px 14px",
            cursor: "pointer",
            fontSize: "14px",
          }}
        >
          Send
        </button>
      </div>
    </div>
  );
}
