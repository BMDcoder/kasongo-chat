import React, { useState, useEffect } from "react";

function Chat({ backendUrl }) {
  const [agentId, setAgentId] = useState(1);
  const [username, setUsername] = useState("guest");
  const [input, setInput] = useState("");
  const [log, setLog] = useState([]);
  const [useGet, setUseGet] = useState(false);

  const send = async () => {
    if (!input) return;

    if (useGet) {
      const params = new URLSearchParams({
        username,
        agent_id: agentId.toString(),
        message: input,
      });

      const res = await fetch(`${backendUrl}/api/chats?${params.toString()}`, {
        method: "GET",
      });

      if (!res.ok) {
        console.error("Chat GET request failed", res.status);
        return;
      }

      const data = await res.json();
      setLog((l) => [
        ...l,
        { role: "user", content: input },
        { role: "agent", content: data.response },
      ]);
    } else {
      const body = { username, agent_id: agentId, message: input };
      const res = await fetch(`${backendUrl}/api/chats`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        console.error("Chat POST request failed", res.status);
        return;
      }

      const data = await res.json();
      setLog((l) => [
        ...l,
        { role: "user", content: input },
        { role: "agent", content: data.response },
      ]);
    }
    setInput("");
  };

  return (
    <div style={{ padding: 20 }}>
      <h2>Kasongo — Chat</h2>
      <div>
        <label>
          Username:{" "}
          <input value={username} onChange={(e) => setUsername(e.target.value)} />
        </label>
        <label style={{ marginLeft: 10 }}>
          Agent ID:{" "}
          <input
            value={agentId}
            onChange={(e) => setAgentId(Number(e.target.value))}
            style={{ width: 60 }}
          />
        </label>
        <label style={{ marginLeft: 20 }}>
          Use GET method:{" "}
          <input
            type="checkbox"
            checked={useGet}
            onChange={(e) => setUseGet(e.target.checked)}
          />
        </label>
      </div>
      <div
        style={{
          border: "1px solid #ddd",
          padding: 10,
          minHeight: 200,
          marginTop: 10,
        }}
      >
        {log.map((m, i) => (
          <div key={i}>
            <strong>{m.role}:</strong> {m.content}
          </div>
        ))}
      </div>
      <div style={{ marginTop: 10 }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          style={{ width: "70%" }}
          placeholder="Ask the agent..."
        />
        <button onClick={send} style={{ marginLeft: 10 }}>
          Send
        </button>
      </div>
    </div>
  );
}

// ... Admin component stays same, App component stays same ...
