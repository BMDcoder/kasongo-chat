import React, { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

export default function App() {
  const [summary, setSummary] = useState("Welcome to the chat");
  const [blocks, setBlocks] = useState([]);
  const [skip, setSkip] = useState(false);
  const scrollRef = useRef(null);
  const timersRef = useRef([]);

  const API_URL = "http://localhost:8000";

  // Fetch previous chat history on mount
  useEffect(() => {
    fetch(`${API_URL}/history`)
      .then((res) => res.json())
      .then((data) => {
        const botMessages = data
          .filter((m) => m.role === "bot")
          .map((m) => m.text);
        setBlocks(botMessages);
      });
  }, []);

  // Display bot chunks with delay
  const showBlocks = (chunks) => {
    setBlocks([]);
    setSkip(false);
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];

    chunks.forEach((text, i) => {
      const timer = setTimeout(() => {
        setBlocks((prev) => [...prev, text]);
        scrollRef.current?.scrollIntoView({ behavior: "smooth" });
      }, i * 1500);
      timersRef.current.push(timer);
    });
  };

  // Send message to backend
  const handleSend = async (msg) => {
    setSummary(msg);
    const res = await fetch(`${API_URL}/send`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role: "user", text: msg }),
    });
    const data = await res.json();
    showBlocks(data.chunks);
  };

  // Tap anywhere to skip chunk pacing
  const handleSkip = () => {
    if (!skip) {
      setSkip(true);
      timersRef.current.forEach(clearTimeout);
      fetch(`${API_URL}/history`)
        .then((res) => res.json())
        .then((data) => {
          const botMessages = data
            .filter((m) => m.role === "bot")
            .map((m) => m.text);
          setBlocks(botMessages);
          scrollRef.current?.scrollIntoView({ behavior: "smooth" });
        });
    }
  };

  // ===== UI Components inside the same file =====

  const Header = ({ summary }) => (
    <header
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "10px 20px",
        borderBottom: "1px solid #ddd",
        background: "#fff",
        position: "sticky",
        top: 0,
        zIndex: 1000,
      }}
    >
      <div style={{ fontWeight: "bold" }}>🤖 Logo</div>
      <div style={{ flex: 1, textAlign: "center", fontSize: "14px" }}>
        <AnimatePresence mode="wait">
          <motion.span
            key={summary}
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 5 }}
            transition={{ duration: 0.3 }}
          >
            {summary}
          </motion.span>
        </AnimatePresence>
      </div>
      <div style={{ width: "40px" }} />
    </header>
  );

  const ChatBlock = ({ text, delay }) => (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.4 }}
      style={{
        background: "#f9f9f9",
        margin: "10px",
        padding: "15px",
        borderRadius: "12px",
        fontSize: "15px",
        lineHeight: "1.4",
      }}
    >
      {text}
    </motion.div>
  );

  const Footer = ({ onSend }) => {
    const [value, setValue] = useState("");
    const handleClick = () => {
      if (value.trim()) {
        onSend(value);
        setValue("");
      }
    };
    return (
      <div
        style={{
          position: "sticky",
          bottom: 0,
          background: "#fff",
          padding: "10px",
          display: "flex",
          gap: "8px",
          borderTop: "1px solid #ddd",
        }}
      >
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Type your message..."
          style={{
            flex: 1,
            padding: "10px",
            borderRadius: "20px",
            border: "1px solid #ccc",
          }}
        />
        <button
          onClick={handleClick}
          style={{
            padding: "10px 15px",
            background: "#007bff",
            color: "#fff",
            border: "none",
            borderRadius: "20px",
            cursor: "pointer",
          }}
        >
          Send
        </button>
      </div>
    );
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      <Header summary={summary} />
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "10px",
          background: "#f0f2f5",
        }}
        onClick={handleSkip}
      >
        {blocks.map((b, i) => (
          <ChatBlock key={i} text={b} delay={0.1} />
        ))}
        <div ref={scrollRef} />
      </div>
      <Footer onSend={handleSend} />
    </div>
  );
}
