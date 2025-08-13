<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Chunked Chatbot UI with Smooth Scroll</title>
<style>
  body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: #f9fafa;
    display: flex;
    flex-direction: column;
    height: 100vh;
    overflow: hidden;
  }
  /* Header */
  .header {
    background: #fff;
    border-bottom: 1px solid #ddd;
    padding: 10px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .logo {
    font-weight: bold;
    color: #0077cc;
  }
  .title {
    flex: 1;
    text-align: center;
    font-size: 14px;
    font-weight: bold;
    animation: fadeIn 0.4s ease;
  }
  /* Scrollable content container */
  .scroll-container {
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column-reverse; /* Latest at bottom */
    scroll-behavior: smooth;
    padding: 10px;
    gap: 10px;
  }
  .block {
    background: #fff;
    padding: 15px;
    border-radius: 8px;
    box-shadow: 0px 2px 6px rgba(0,0,0,0.1);
    width: 85%;
    max-width: 500px;
    align-self: center;
    animation: slideUp 0.5s ease;
  }
  .highlight {
    background: #d0ebff;
    padding: 2px 4px;
    border-radius: 4px;
  }
  /* Footer */
  .footer {
    background: #fff;
    border-top: 1px solid #ddd;
    padding: 10px;
  }
  .quick-actions {
    display: flex;
    gap: 6px;
    margin-bottom: 8px;
  }
  .quick-btn {
    background: #f1f3f5;
    border: none;
    padding: 5px 10px;
    border-radius: 20px;
    cursor: pointer;
    font-size: 12px;
  }
  .input-area {
    display: flex;
    gap: 8px;
  }
  .input-area input {
    flex: 1;
    padding: 8px;
    border-radius: 20px;
    border: 1px solid #ccc;
  }
  .input-area button {
    background: #0077cc;
    border: none;
    color: white;
    padding: 8px 14px;
    border-radius: 20px;
    cursor: pointer;
  }
  /* Animations */
  @keyframes slideUp {
    from { transform: translateY(30px); opacity: 0; }
    to { transform: translateY(0); opacity: 1; }
  }
  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }
</style>
</head>
<body>

<!-- Header -->
<div class="header">
  <div class="logo">🤖 MyBot</div>
  <div class="title" id="header-title">Simple Quantum Computing</div>
  <div style="width:40px;"></div>
</div>

<!-- Scrollable Content -->
<div class="scroll-container" id="scroll-container"></div>

<!-- Footer -->
<div class="footer">
  <div class="quick-actions">
    <button class="quick-btn">Explain in more detail</button>
    <button class="quick-btn">Give real-world example</button>
    <button class="quick-btn">Show diagram</button>
  </div>
  <div class="input-area">
    <input type="text" placeholder="Ask me something..." />
    <button>Send</button>
  </div>
</div>

<script>
  const blocks = [
    "Quantum computing uses quantum bits, or <span class='highlight'>qubits</span>, instead of regular bits. Qubits can represent both 0 and 1 at the same time thanks to <span class='highlight'>superposition</span>.",
    "This lets quantum computers solve certain problems much faster than normal computers.",
    "Tip: <span class='highlight'>Superposition</span> means a particle can be in multiple states at once."
  ];

  let index = 0;
  const container = document.getElementById("scroll-container");

  function showNextBlock() {
    if (index < blocks.length) {
      const block = document.createElement("div");
      block.className = "block";
      block.innerHTML = blocks[index];
      container.prepend(block); // Add to bottom visually (since flex-direction is reverse)
      index++;
    }
  }

  // Auto progress every 3 seconds, allow click to skip
  showNextBlock();
  let timer = setInterval(showNextBlock, 3000);
  container.addEventListener("click", () => {
    clearInterval(timer);
    showNextBlock();
  });
</script>

</body>
</html>
