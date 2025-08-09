import React, {useState, useEffect} from "react";

function Chat({ backendUrl }) {
  const [agentId, setAgentId] = useState(1);
  const [username, setUsername] = useState("guest");
  const [input, setInput] = useState("");
  const [log, setLog] = useState([]);

  const send = async () => {
    if(!input) return;
    const body = { username, agent_id: agentId, message: input };
    const res = await fetch(`${backendUrl}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    const data = await res.json();
    setLog(l => [...l, { role: "user", content: input }, { role: "agent", content: data.response }]);
    setInput("");
  };

  return (
    <div style={{padding:20}}>
      <h2>Kasongo — Chat</h2>
      <div>
        <label>Username: <input value={username} onChange={e=>setUsername(e.target.value)} /></label>
        <label style={{marginLeft:10}}>Agent ID: <input value={agentId} onChange={e=>setAgentId(Number(e.target.value))} style={{width:60}} /></label>
      </div>
      <div style={{border:"1px solid #ddd", padding:10, minHeight:200, marginTop:10}}>
        {log.map((m,i)=>(<div key={i}><strong>{m.role}:</strong> {m.content}</div>))}
      </div>
      <div style={{marginTop:10}}>
        <input value={input} onChange={e=>setInput(e.target.value)} style={{width:"70%"}} placeholder="Ask the agent..." />
        <button onClick={send} style={{marginLeft:10}}>Send</button>
      </div>
    </div>
  )
}

function Admin({ backendUrl }) {
  const [token, setToken] = useState("");
  const [agents, setAgents] = useState([]);
  const [form, setForm] = useState({name:"Local Marketer", system_prompt:"You are a professional local marketing consultant.", description:""});

  useEffect(()=>{ if(token) loadAgents(); }, [token]);

  const login = async () => {
    const res = await fetch(`${backendUrl}/admin/login`, {
      method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({username:"admin", password:"adminpass"})
    });
    const data = await res.json();
    setToken(data.access_token);
  };

  const loadAgents = async () => {
    const res = await fetch(`${backendUrl}/admin/agents`, { headers: { Authorization: "Bearer " + token }});
    const data = await res.json();
    setAgents(data);
  };

  const createAgent = async () => {
    await fetch(`${backendUrl}/admin/agents`, { method:"POST", headers: { "Content-Type":"application/json", Authorization: "Bearer " + token }, body: JSON.stringify(form) });
    loadAgents();
  };

  return (
    <div style={{padding:20}}>
      <h2>Admin</h2>
      {!token ? <button onClick={login}>Login as default admin</button> : <>
        <div>
          <h3>Create Agent</h3>
          <label>Name: <input value={form.name} onChange={e=>setForm({...form,name:e.target.value})} /></label><br/>
          <label>System prompt:<br/><textarea value={form.system_prompt} onChange={e=>setForm({...form,system_prompt:e.target.value})} rows={4} cols={60} /></label><br/>
          <button onClick={createAgent}>Create</button>
        </div>
        <div>
          <h3>Agents</h3>
          <ul>
            {agents.map((a,i)=>(<li key={i}>{a.name}</li>))}
          </ul>
        </div>
      </>}
    </div>
  )
}

export default function App(){
  const backendUrl = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";
  const [page, setPage] = useState("chat");
  return (
    <div>
      <div style={{padding:10, borderBottom:"1px solid #ddd"}}>
        <button onClick={()=>setPage("chat")}>Chat</button>
        <button onClick={()=>setPage("admin")} style={{marginLeft:10}}>Admin</button>
      </div>
      {page==="chat" ? <Chat backendUrl={backendUrl} /> : <Admin backendUrl={backendUrl} />}
    </div>
  )
}
