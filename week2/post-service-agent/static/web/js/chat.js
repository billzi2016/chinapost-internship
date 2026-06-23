const sftToggle = document.getElementById("use-sft");
const sftWarning = document.getElementById("sft-warning");
const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");
const messages = document.getElementById("messages");

function appendMessage(role, html) {
  const node = document.createElement("article");
  node.className = `message ${role}`;
  node.innerHTML = html;
  messages.appendChild(node);
  messages.scrollTop = messages.scrollHeight;
  return node;
}

function appendToMessage(node, html) {
  node.innerHTML += html;
  messages.scrollTop = messages.scrollHeight;
}

function renderMarkdown(text) {
  if (!window.marked || !window.DOMPurify) {
    return text;
  }
  return DOMPurify.sanitize(marked.parse(text));
}

function parseSseBlock(block) {
  const eventLine = block.split("\n").find((line) => line.startsWith("event: "));
  const dataLine = block.split("\n").find((line) => line.startsWith("data: "));
  if (!eventLine || !dataLine) return null;
  return {
    event: eventLine.replace("event: ", "").trim(),
    data: JSON.parse(dataLine.replace("data: ", ""))
  };
}

async function consumeSse(response, assistantNode) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let answer = "";
  let citations = [];

  while (true) {
    const {done, value} = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, {stream: true});
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop();

    for (const block of blocks) {
      const parsed = parseSseBlock(block);
      if (!parsed) continue;

      if (parsed.event === "error") {
        assistantNode.innerHTML = `<p class="text-danger">${parsed.data.message}</p>`;
      }

      if (parsed.event === "citation") {
        citations.push(parsed.data);
      }

      if (parsed.event === "delta") {
        answer += parsed.data.content;
        assistantNode.innerHTML = renderMarkdown(answer);
      }

      if (parsed.event === "ticket") {
        appendToMessage(
          assistantNode,
          `<section class="ticket-json"><h2>工单 JSON</h2><pre>${JSON.stringify(parsed.data.payload, null, 2)}</pre></section>`
        );
      }

      if (parsed.event === "done" && citations.length) {
        const items = citations.map((item) => (
          `<details class="citation"><summary>引用 ${item.rank} · score ${item.score.toFixed(4)}</summary><pre>${item.quoted_text}</pre></details>`
        )).join("");
        appendToMessage(assistantNode, `<section class="citations"><h2>引用对话</h2>${items}</section>`);
      }
    }
  }
}

sftToggle?.addEventListener("change", () => {
  sftWarning.hidden = !sftToggle.checked;
});

form?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const content = input.value.trim();
  if (!content) return;
  appendMessage("user", renderMarkdown(content));
  input.value = "";

  const loading = appendMessage("assistant", '<span class="typing"><span>●</span><span>●</span><span>●</span></span>');
  const response = await fetch("/api/chat/stream", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      message: content,
      use_rag: document.getElementById("use-rag").checked,
      use_sft: sftToggle.checked
    })
  });
  await consumeSse(response, loading);
});
