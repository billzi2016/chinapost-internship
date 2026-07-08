const sftToggle = document.getElementById("use-sft");
const sftWarning = document.getElementById("sft-warning");
const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");
const messages = document.getElementById("messages");
const conversationIdInput = document.getElementById("conversation-id");
const conversationList = document.querySelector(".conversation-list");
const ticketPanel = document.getElementById("ticket-panel");
const generateTicketButton = document.getElementById("generate-ticket");
const viewTicketButton = document.getElementById("view-ticket");
const providerHealth = document.getElementById("provider-health");
const newChatButton = document.getElementById("new-chat");
let retryDraft = null;
let sftConfigured = false;

document.addEventListener("DOMContentLoaded", () => {
  if (window.Split) {
    Split([".sidebar", ".chat-panel"], {minSize: 240});
  }
  loadProviderHealth();
  bindTicketPanelResize();
  bindComposerResize();
});

function formatDateTime(value) {
  const date = value ? new Date(value) : new Date();
  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false
  });
}

function appendMessage(role, html, createdAt = null, messageId = null) {
  const node = document.createElement("article");
  node.className = `message ${role}`;
  if (messageId) node.dataset.messageId = String(messageId);
  node.innerHTML = `
    <div class="message-body">${html}</div>
    <time class="message-time" datetime="${createdAt || new Date().toISOString()}">${formatDateTime(createdAt)}</time>
  `;
  messages.appendChild(node);
  messages.scrollTop = messages.scrollHeight;
  return node;
}

function appendUserMessage(content, createdAt = null, messageId = null, canRetry = false) {
  const action = canRetry
    ? `<div class="message-actions">
        <button class="message-edit-last" type="button" title="修改上一条问题" data-message-id="${escapeHtml(messageId)}" data-content="${escapeHtml(content)}">修改</button>
        <button class="message-retry-last" type="button" title="基于上一条问题重新回答" data-message-id="${escapeHtml(messageId)}" data-content="${escapeHtml(content)}">重新回答</button>
      </div>`
    : "";
  return appendMessage(
    "user",
    `${renderMarkdown(content)}${action}`,
    createdAt,
    messageId
  );
}

function appendToMessage(node, html) {
  const body = node.querySelector(".message-body");
  if (body) {
    body.innerHTML += html;
  } else {
    node.innerHTML += html;
  }
  messages.scrollTop = messages.scrollHeight;
}

function clearRetryButtons() {
  document.querySelectorAll(".message-edit-last").forEach((button) => button.remove());
}

function startThinkingAnimation(node) {
  const dots = Array.from(node.querySelectorAll(".typing-dot"));
  if (!dots.length) return;
  let index = 0;
  dots[0].classList.add("active");
  node.thinkingTimer = window.setInterval(() => {
    dots.forEach((dot) => dot.classList.remove("active"));
    dots[index % dots.length].classList.add("active");
    index += 1;
  }, 180);
}

function stopThinkingAnimation(node) {
  if (node?.thinkingTimer) {
    window.clearInterval(node.thinkingTimer);
    node.thinkingTimer = null;
  }
}

function renderMarkdown(text) {
  if (!window.marked || !window.DOMPurify) {
    return escapeHtml(text);
  }
  return DOMPurify.sanitize(marked.parse(text), {
    ALLOWED_URI_REGEXP: /^(?:(?:https?|mailto|tel):|[^a-z]|[a-z+.\-]+(?:[^a-z+.\-:]|$))/i
  });
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function titleCaseWords(value) {
  return String(value || "")
    .split(/([/_-])/)
    .map((part) => /^[a-zA-Z0-9]/.test(part) ? part.charAt(0).toUpperCase() + part.slice(1) : part)
    .join("");
}

function formatProviderName(value) {
  const key = String(value || "").toLowerCase();
  if (key === "faiss") return "FAISS";
  if (key === "pgvector") return "PostgreSQL-Pgvector";
  return titleCaseWords(value);
}

function formatModelName(value) {
  const key = String(value || "").toLowerCase();
  if (key === "gpt-oss:20b") return "GPT-OSS:20B";
  return titleCaseWords(value);
}

function getCookie(name) {
  return document.cookie
    .split(";")
    .map((item) => item.trim())
    .find((item) => item.startsWith(`${name}=`))
    ?.slice(name.length + 1) || "";
}

function csrfFetch(url, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set("X-CSRFToken", decodeURIComponent(getCookie("csrftoken")));
  return fetch(url, {
    ...options,
    headers,
    credentials: "same-origin"
  });
}

function renderConversationTitle(conversation) {
  const title = conversation.title || "未命名会话";
  const error = conversation.latest_error || "";
  const titleClass = error && title === error ? "conversation-title error" : "conversation-title";
  const errorLine = error && title !== error
    ? `<span class="conversation-error">${escapeHtml(error)}</span>`
    : "";
  return `
    <span class="${titleClass}">${escapeHtml(title)}</span>
    ${errorLine}
  `;
}

function renderCitationText(text) {
  return String(text || "").split("\n").filter(Boolean).map((line) => {
    const match = line.match(/^((?:用户|客服)\[\d+\]:)(.*)$/);
    if (!match) {
      return `<p class="citation-line">${escapeHtml(line)}</p>`;
    }
    const roleClass = match[1].startsWith("用户") ? "user" : "agent";
    return `
      <p class="citation-line">
        <strong class="citation-speaker ${roleClass}">${escapeHtml(match[1])}</strong>
        <span class="citation-content">${escapeHtml(match[2].trim())}</span>
      </p>
    `;
  }).join("");
}

function renderTicketValue(value, fallback = "无") {
  const text = String(value || fallback);
  return renderMarkdown(text);
}

function renderCitations(citations) {
  if (!citations || !citations.length) return "";
  const items = citations.map((item, index) => {
    const rank = item.rank || index + 1;
    return `<details class="citation"><summary>引用 ${rank} · score ${Number(item.score).toFixed(4)}</summary><div class="citation-body">${renderCitationText(item.quoted_text)}</div></details>`;
  }).join("");
  return `<section class="citations"><h2>引用对话</h2>${items}</section>`;
}

function bindTicketPanelResize() {
  const handle = document.getElementById("ticket-resize-handle");
  if (!handle || !ticketPanel) return;

  let startY = 0;
  let startHeight = 0;

  handle.addEventListener("pointerdown", (event) => {
    startY = event.clientY;
    startHeight = ticketPanel.getBoundingClientRect().height;
    handle.setPointerCapture(event.pointerId);
    document.body.classList.add("is-ticket-resizing");
  });

  handle.addEventListener("pointermove", (event) => {
    if (!handle.hasPointerCapture(event.pointerId)) return;
    const nextHeight = startHeight + startY - event.clientY;
    ticketPanel.style.height = `${Math.min(Math.max(nextHeight, 160), 520)}px`;
  });

  handle.addEventListener("pointerup", (event) => {
    if (handle.hasPointerCapture(event.pointerId)) {
      handle.releasePointerCapture(event.pointerId);
    }
    document.body.classList.remove("is-ticket-resizing");
  });
}

function bindComposerResize() {
  const handle = document.getElementById("composer-resize-handle");
  if (!handle || !form) return;

  let startY = 0;
  let startHeight = 0;

  handle.addEventListener("pointerdown", (event) => {
    startY = event.clientY;
    startHeight = form.getBoundingClientRect().height;
    handle.setPointerCapture(event.pointerId);
    document.body.classList.add("is-composer-resizing");
  });

  handle.addEventListener("pointermove", (event) => {
    if (!handle.hasPointerCapture(event.pointerId)) return;
    const nextHeight = startHeight + startY - event.clientY;
    form.style.height = `${Math.min(Math.max(nextHeight, 74), 240)}px`;
  });

  handle.addEventListener("pointerup", (event) => {
    if (handle.hasPointerCapture(event.pointerId)) {
      handle.releasePointerCapture(event.pointerId);
    }
    document.body.classList.remove("is-composer-resizing");
  });
}

async function refreshConversations(activeId) {
  const response = await fetch("/api/conversations");
  const conversations = await response.json();
  conversationList.innerHTML = conversations.length ? "" : '<span class="empty-list">暂无会话</span>';
  for (const conversation of conversations) {
    const row = document.createElement("div");
    row.className = `conversation-row ${conversation.id === activeId ? "active" : ""} ${conversation.is_pinned ? "pinned" : ""}`;
    row.dataset.id = conversation.id;
    row.innerHTML = `
      <button class="conversation-item" type="button">${renderConversationTitle(conversation)}</button>
      <button class="icon-button pin-conversation" type="button" title="置顶" aria-label="置顶">📌</button>
      <button class="icon-button delete-conversation" type="button" title="删除">×</button>
    `;
    conversationList.appendChild(row);
  }
}

function resetCurrentConversation() {
  conversationIdInput.value = "";
  messages.innerHTML = "";
  retryDraft = null;
  renderTicket(null);
  document.querySelectorAll(".conversation-row").forEach((row) => row.classList.remove("active"));
  input.focus();
}

async function loadConversation(conversationId) {
  conversationIdInput.value = conversationId;
  messages.innerHTML = "";
  renderTicket(null);
  document.querySelectorAll(".conversation-row").forEach((row) => row.classList.remove("active"));
  document.querySelector(`.conversation-row[data-id="${conversationId}"]`)?.classList.add("active");
  const response = await fetch(`/api/conversations/${conversationId}/messages`);
  const items = await response.json();
  const lastUser = [...items].reverse().find((item) => item.role === "user");
  for (const item of items) {
    if (item.role === "user") {
      appendUserMessage(item.content, item.created_at, item.id, lastUser && item.id === lastUser.id);
    } else {
      appendMessage(item.role, renderMarkdown(item.content) + renderCitations(item.citations), item.created_at, item.id);
    }
  }
  await loadTicket(conversationId);
}

async function loadProviderHealth() {
  try {
    const response = await fetch("/api/provider/health");
    if (!response.ok) throw new Error("provider health unavailable");
    const health = await response.json();
    sftConfigured = Boolean(health.sft_configured);
    updateSftWarning();
    providerHealth.innerHTML = `
      <span class="health-item">
        <span class="health-dot ok" aria-hidden="true"></span>
        Chat Provider: ${escapeHtml(formatProviderName(health.chat_provider))}/${escapeHtml(formatModelName(health.chat_model))}
      </span>
      <span class="health-item">
        <span class="health-dot ok" aria-hidden="true"></span>
        Vector Provider: ${escapeHtml(formatProviderName(health.vector_provider))}
      </span>
      <span class="health-item">
        <span class="health-dot ${sftConfigured ? "ok" : "bad"}" aria-hidden="true"></span>
        SFT: ${sftConfigured ? "Ready" : "Unavailable"}
      </span>
    `;
  } catch {
    sftConfigured = false;
    updateSftWarning();
    providerHealth.innerHTML = `
      <span class="health-item">
        <span class="health-dot bad" aria-hidden="true"></span>
        Chat Provider: Unavailable
      </span>
      <span class="health-item">
        <span class="health-dot bad" aria-hidden="true"></span>
        Vector Provider: Unavailable
      </span>
      <span class="health-item">
        <span class="health-dot bad" aria-hidden="true"></span>
        SFT: Unavailable
      </span>
    `;
  }
}

function updateSftWarning() {
  if (!sftWarning || !sftToggle) return;
  sftWarning.hidden = !sftToggle.checked || sftConfigured;
}

function renderTicket(ticket) {
  if (!ticket) {
    ticketPanel.hidden = true;
    ticketPanel.innerHTML = "";
    return;
  }
  const payload = ticket.payload;
  const jsonText = JSON.stringify(payload, null, 2);
  ticketPanel.hidden = false;
  ticketPanel.innerHTML = `
    <div class="ticket-resize-handle" id="ticket-resize-handle" aria-hidden="true"></div>
    <button class="ticket-close" type="button" id="close-ticket" title="关闭工单">×</button>
    <section class="ticket-layout">
      <div class="ticket-readable" aria-label="工单摘要">
        <h2>工单摘要</h2>
        <dl>
          <dt>服务类型</dt>
          <dd>${renderTicketValue(payload.service_type, "未识别")}</dd>
          <dt>问题类型</dt>
          <dd>${renderTicketValue(payload.issue_type, "未识别")}</dd>
          <dt>用户请求</dt>
          <dd>${renderTicketValue(payload.user_request)}</dd>
          <dt>处理摘要</dt>
          <dd>${renderTicketValue(payload.summary)}</dd>
          <dt>处理结果</dt>
          <dd>${renderTicketValue(payload.resolution)}</dd>
          <dt>是否需要跟进</dt>
          <dd>${payload.need_follow_up ? "需要" : "不需要"}</dd>
        </dl>
      </div>
      <div class="ticket-json">
        <div class="ticket-json-header">
          <h2>工单 JSON</h2>
          <p class="ticket-note">首次生成后锁定，重复点击不覆盖。</p>
        </div>
        <div class="ticket-codebox">
          <div class="ticket-json-actions">
            <button class="btn btn-sm btn-light" type="button" id="copy-ticket-json">复制 JSON</button>
            <button class="btn btn-sm btn-light" type="button" id="download-ticket">下载 JSON</button>
          </div>
          <pre>${escapeHtml(jsonText)}</pre>
        </div>
      </div>
    </section>
  `;
  bindTicketPanelResize();
  document.getElementById("copy-ticket-json")?.addEventListener("click", async () => {
    await navigator.clipboard.writeText(jsonText);
  });
  document.getElementById("download-ticket")?.addEventListener("click", () => {
    const blob = new Blob([jsonText], {type: "application/json"});
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `ticket-${ticket.id}.json`;
    link.click();
    URL.revokeObjectURL(url);
  });
  document.getElementById("close-ticket")?.addEventListener("click", () => {
    renderTicket(null);
  });
}

async function loadTicket(conversationId) {
  const response = await fetch(`/api/conversations/${conversationId}/ticket`);
  if (!response.ok) return;
  renderTicket(await response.json());
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

      if (parsed.event === "meta") {
        conversationIdInput.value = parsed.data.conversation_id;
      }

      if (parsed.event === "error") {
        stopThinkingAnimation(assistantNode);
        const body = assistantNode.querySelector(".message-body");
        if (body) body.innerHTML = `<p class="text-danger">${escapeHtml(parsed.data.message)}</p>`;
      }

      if (parsed.event === "citation") {
        citations.push(parsed.data);
      }

      if (parsed.event === "delta") {
        stopThinkingAnimation(assistantNode);
        answer += parsed.data.content;
        const body = assistantNode.querySelector(".message-body");
        if (body) body.innerHTML = renderMarkdown(answer);
      }

      if (parsed.event === "done" && citations.length) {
        stopThinkingAnimation(assistantNode);
        appendToMessage(assistantNode, renderCitations(citations));
      }

      if (parsed.event === "done") {
        stopThinkingAnimation(assistantNode);
      }
    }
  }
}

sftToggle?.addEventListener("change", () => {
  updateSftWarning();
});

newChatButton?.addEventListener("click", () => {
  resetCurrentConversation();
});

messages?.addEventListener("click", (event) => {
  const button = event.target.closest(".message-edit-last, .message-retry-last");
  if (!button) return;
  const node = button.closest(".message.user");
  if (!node) return;
  const body = node.querySelector(".message-body");
  retryDraft = {
    conversationId: Number(conversationIdInput.value),
    messageId: Number(button.dataset.messageId),
    messageNode: node,
    original: button.dataset.content || body?.innerText.trim() || ""
  };
  if (button.classList.contains("message-retry-last")) {
    input.value = retryDraft.original;
    form.requestSubmit();
    return;
  }
  input.value = retryDraft.original;
  input.focus();
});

input?.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

form?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const content = input.value.trim();
  if (!content) return;
  if (retryDraft?.conversationId) {
    const draft = retryDraft;
    retryDraft = null;
    draft.messageNode.querySelector(".message-body").innerHTML = `${renderMarkdown(content)}<div class="message-actions">
      <button class="message-edit-last" type="button" title="修改上一条问题" data-message-id="${escapeHtml(draft.messageId)}" data-content="${escapeHtml(content)}">修改</button>
      <button class="message-retry-last" type="button" title="基于上一条问题重新回答" data-message-id="${escapeHtml(draft.messageId)}" data-content="${escapeHtml(content)}">重新回答</button>
    </div>`;
    let next = draft.messageNode.nextElementSibling;
    while (next) {
      const current = next;
      next = next.nextElementSibling;
      current.remove();
    }
    renderTicket(null);
    input.value = "";
    const loading = appendMessage("assistant", '<span class="typing"><span class="typing-label">Thinking</span><span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span></span>');
    startThinkingAnimation(loading);
    const response = await csrfFetch(`/api/conversations/${draft.conversationId}/last-user-message/retry`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        message_id: draft.messageId,
        message: content,
        use_rag: document.getElementById("use-rag").checked,
        use_sft: sftToggle.checked
      })
    });
    await consumeSse(response, loading);
    await loadConversation(Number(conversationIdInput.value));
    await refreshConversations(Number(conversationIdInput.value) || null);
    return;
  }

  clearRetryButtons();
  appendUserMessage(content);
  input.value = "";

  const loading = appendMessage("assistant", '<span class="typing"><span class="typing-label">Thinking</span><span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span></span>');
  startThinkingAnimation(loading);
  const response = await csrfFetch("/api/chat/stream", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      conversation_id: conversationIdInput.value ? Number(conversationIdInput.value) : null,
      message: content,
      use_rag: document.getElementById("use-rag").checked,
      use_sft: sftToggle.checked
    })
  });
  await consumeSse(response, loading);
  await loadConversation(Number(conversationIdInput.value));
  await refreshConversations(Number(conversationIdInput.value) || null);
});

generateTicketButton?.addEventListener("click", async () => {
  const conversationId = conversationIdInput.value;
  if (!conversationId) {
    ticketPanel.hidden = false;
    ticketPanel.innerHTML = '<p class="text-danger">请先选择或发送一个会话。</p>';
    return;
  }
  const response = await csrfFetch(`/api/conversations/${conversationId}/ticket/generate`, {
    method: "POST"
  });
  if (!response.ok) {
    ticketPanel.hidden = false;
    ticketPanel.innerHTML = '<p class="text-danger">工单生成失败。</p>';
    return;
  }
  renderTicket(await response.json());
});

viewTicketButton?.addEventListener("click", async () => {
  const conversationId = conversationIdInput.value;
  if (!conversationId) {
    ticketPanel.hidden = false;
    ticketPanel.innerHTML = '<p class="text-danger">请先选择一个会话。</p>';
    return;
  }
  await loadTicket(conversationId);
});

conversationList?.addEventListener("click", async (event) => {
  const row = event.target.closest(".conversation-row");
  if (!row) return;
  const conversationId = Number(row.dataset.id);

  if (event.target.classList.contains("delete-conversation")) {
    await csrfFetch(`/api/conversations/${conversationId}`, {method: "DELETE"});
    if (conversationIdInput.value === String(conversationId)) {
      conversationIdInput.value = "";
      messages.innerHTML = "";
      renderTicket(null);
    }
    await refreshConversations(null);
    return;
  }

  if (event.target.classList.contains("pin-conversation")) {
    await csrfFetch(`/api/conversations/${conversationId}/pin`, {method: "PATCH"});
    await refreshConversations(conversationId);
    return;
  }

  await loadConversation(conversationId);
});
