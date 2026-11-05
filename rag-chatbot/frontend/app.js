// ── Fix broken emoji images on Windows ──
// Catch any <img> that fails to load (browser-generated emoji images) and remove it
document.addEventListener("error", function(e) {
    if (e.target.tagName === "IMG") {
        e.target.style.display = "none";
        e.target.remove();
    }
}, true);
// Also observe DOM for dynamically added broken images
new MutationObserver(function(mutations) {
    mutations.forEach(function(m) {
        m.addedNodes.forEach(function(node) {
            if (node.nodeType === 1) {
                node.querySelectorAll && node.querySelectorAll("img").forEach(function(img) {
                    img.style.display = "none";
                    img.addEventListener("error", function() { img.remove(); });
                    // If already broken (no natural dimensions and no valid src)
                    if (!img.naturalWidth && !img.closest(".logo")) img.remove();
                });
            }
        });
    });
}).observe(document.body, { childList: true, subtree: true });

const messagesEl = document.getElementById("messages");
const userInput = document.getElementById("userInput");
const sendBtn = document.getElementById("sendBtn");
const statusIndicator = document.getElementById("statusIndicator");
let welcomeInput = document.getElementById("welcomeInput");
let welcomeSendBtn = document.getElementById("welcomeSendBtn");

// Popup elements
const chatbotFab = document.getElementById("chatbotFab");
const chatbotPopup = document.getElementById("chatbotPopup");
const popupCloseBtn = document.getElementById("popupCloseBtn");

// Session ID — fresh on every page load (each visit = new session)
let sessionId = "s_" + Math.random().toString(36).slice(2, 10) + Date.now().toString(36);

// Batched event tracking — buffer events and flush every 2 seconds
let _trackBuffer = [];
let _trackTimer = null;

function _flushTrackBuffer() {
    if (_trackBuffer.length === 0) return;
    const events = _trackBuffer.splice(0);
    for (const evt of events) {
        fetch("/track", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(evt),
        }).catch(() => {});
    }
}

function trackEvent(eventType, eventData) {
    _trackBuffer.push({
        session_id: sessionId,
        event_type: eventType,
        event_data: eventData || {},
        page_url: window.location.pathname,
    });
    if (!_trackTimer) {
        _trackTimer = setTimeout(() => {
            _trackTimer = null;
            _flushTrackBuffer();
        }, 2000);
    }
}

// Clear any stale session data from previous visits
localStorage.removeItem("sparrowi_session_id");
localStorage.removeItem("sparrowi_history");
localStorage.removeItem("sparrowi_messages");

// Conversation history (in-memory only, capped at 10)
const MAX_HISTORY = 20;
let conversationHistory = [];

// --- Report Issue mode ---
let reportIssueMode = false;

// --- Feedback ---
let botMessageIndex = 0;

// --- TTS (Text-to-Speech) ---
let activeTtsBtn = null;

function stripHtml(html) {
    const tmp = document.createElement("div");
    tmp.innerHTML = html;
    return tmp.textContent || "";
}

function speakText(text, btnEl) {
    // Toggle off if already speaking this button
    if (activeTtsBtn === btnEl) {
        stopSpeech();
        return;
    }
    // Cancel any ongoing speech first
    stopSpeech();

    const utterance = new SpeechSynthesisUtterance(text);
    activeTtsBtn = btnEl;
    btnEl.classList.add("speaking");
    btnEl.title = "Stop reading";
    btnEl.querySelector(".tts-icon-speak").style.display = "none";
    btnEl.querySelector(".tts-icon-stop").style.display = "inline";

    const resetBtn = () => {
        btnEl.classList.remove("speaking");
        btnEl.title = "Read aloud";
        btnEl.querySelector(".tts-icon-speak").style.display = "inline";
        btnEl.querySelector(".tts-icon-stop").style.display = "none";
        if (activeTtsBtn === btnEl) activeTtsBtn = null;
    };

    utterance.onend = resetBtn;
    utterance.onerror = resetBtn;
    speechSynthesis.speak(utterance);
}

function stopSpeech() {
    speechSynthesis.cancel();
    if (activeTtsBtn) {
        activeTtsBtn.classList.remove("speaking");
        activeTtsBtn.title = "Read aloud";
        const speakIcon = activeTtsBtn.querySelector(".tts-icon-speak");
        const stopIcon = activeTtsBtn.querySelector(".tts-icon-stop");
        if (speakIcon) speakIcon.style.display = "inline";
        if (stopIcon) stopIcon.style.display = "none";
        activeTtsBtn = null;
    }
}

// Auto-resize textarea
userInput.addEventListener("input", () => {
    userInput.style.height = "auto";
    userInput.style.height = Math.min(userInput.scrollHeight, 120) + "px";
});

// Send on Enter (Shift+Enter for newline)
userInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// Welcome search box listeners
function bindWelcomeInputListeners() {
    welcomeInput = document.getElementById("welcomeInput");
    welcomeSendBtn = document.getElementById("welcomeSendBtn");

    if (welcomeInput) {
        welcomeInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                sendMessage(welcomeInput.value);
            }
        });
    }

    if (welcomeSendBtn) {
        welcomeSendBtn.addEventListener("click", () => {
            sendMessage(welcomeInput.value);
        });
    }

    // Re-bind welcome mic button
    const welcomeMicBtn = document.getElementById("welcomeMicBtn");
    if (welcomeMicBtn && typeof bindMicButton === "function") {
        bindMicButton(welcomeMicBtn);
    }
}

bindWelcomeInputListeners();

sendBtn.addEventListener("click", sendMessage);

// ── Welcome typing animation ──
const WELCOME_TEXT = "Hi there! I'm Sparrowi, your dedicated assistant. Ask me anything about our services, projects, clients, or company — I'm here to help you explore everything Sparrow Interactive has to offer.";
let welcomeTyped = false;
let welcomeTypingTimer = null;

function typeWelcomeText() {
    const el = document.getElementById("welcomeTypingText");
    if (!el || welcomeTyped) return;
    welcomeTyped = true;

    let i = 0;
    el.textContent = "";
    function typeNext() {
        if (i < WELCOME_TEXT.length) {
            el.textContent += WELCOME_TEXT[i];
            i++;
            // Scroll the messages area as text grows
            messagesEl.scrollTop = messagesEl.scrollHeight;
            welcomeTypingTimer = setTimeout(typeNext, 18);
        }
    }
    typeNext();
}

// ── Load randomized initial suggestions from backend ──
function loadInitialSuggestions() {
    const container = document.getElementById("initialSuggestions");
    if (!container) return;
    fetch("/api/initial-suggestions")
        .then(r => r.json())
        .then(data => {
            const suggestions = data.suggestions || [];
            container.innerHTML = suggestions.map(s =>
                `<span class="suggested-item" onclick="sendMessage('${s.replace(/'/g, "\\'")}')">${s}</span>`
            ).join("");
        })
        .catch(() => {
            // Fallback if API fails — show nothing rather than stale suggestions
            container.innerHTML = "";
        });
}

// ── Popup open/close ──
function openChatPopup() {
    chatbotPopup.classList.remove("closing");
    chatbotPopup.classList.add("open");
    chatbotFab.classList.add("hidden");
    // Restart health polling if it was stopped
    if (!healthInterval) { healthInterval = setInterval(checkHealth, 15000); }
    // Focus the appropriate input
    const wi = document.getElementById("welcomeInput");
    if (wi) {
        wi.focus();
    } else {
        userInput.focus();
    }
    // Start typing animation
    typeWelcomeText();
    // Load randomized initial suggestions
    loadInitialSuggestions();
    // Track chat opened
    trackEvent("chat_opened");
}

function closeChatPopup() {
    if (!chatbotPopup.classList.contains("open")) return;
    stopSpeech();
    // Flush any pending tracked events and stop health polling
    _flushTrackBuffer();
    if (healthInterval) { clearInterval(healthInterval); healthInterval = null; }
    chatbotPopup.classList.remove("open");
    chatbotPopup.classList.add("closing");

    chatbotPopup.addEventListener("animationend", function handler() {
        chatbotPopup.classList.remove("closing");
        chatbotFab.classList.remove("hidden");
        chatbotPopup.removeEventListener("animationend", handler);
    });
}

chatbotFab.addEventListener("click", (e) => {
    e.stopPropagation();
    openChatPopup();
});
popupCloseBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    closeChatPopup();
});

// Block ALL clicks inside the popup from reaching the document listener
chatbotPopup.addEventListener("click", (e) => {
    e.stopPropagation();
});

// Escape key closes popup
document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && chatbotPopup.classList.contains("open")) {
        closeChatPopup();
    }
});

// Click outside popup — close
document.addEventListener("click", () => {
    if (chatbotPopup.classList.contains("open")) {
        closeChatPopup();
    }
});

// Health check polling
async function checkHealth() {
    try {
        const res = await fetch("/health");
        const data = await res.json();
        statusIndicator.className = "status-indicator " + (data.qdrant ? "connected" : "disconnected");
        statusIndicator.title = data.qdrant ? "Connected" : "Qdrant unavailable";
    } catch {
        statusIndicator.className = "status-indicator disconnected";
        statusIndicator.title = "Server unavailable";
    }
}

checkHealth();
let healthInterval = setInterval(checkHealth, 15000);

// Load initial suggestions on page load (for the pre-rendered welcome card)
loadInitialSuggestions();

// Welcome card HTML template (for soft reset)
const welcomeCardHTML = `
<div class="welcome-card">
    <div class="welcome-icon">
        <svg viewBox="0 0 24 24" width="32" height="32" fill="currentColor">
            <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H5.17L4 17.17V4h16v12z"/>
            <path d="M12 10c.55 0 1-.45 1-1V7c0-.55-.45-1-1-1s-1 .45-1 1v2c0 .55.45 1 1 1zm0 2c-.55 0-1 .45-1 1s.45 1 1 1 1-.45 1-1-.45-1-1-1z"/>
        </svg>
    </div>
    <h2>Welcome to Sparrow Interactive</h2>
    <p id="welcomeTypingText"></p>
    <div class="welcome-chips">
        <span class="chip" onclick="sendMessage('What services does Sparrow Interactive offer?')">Our Services</span>
        <span class="chip" onclick="sendMessage('Show me your projects and portfolio')">Projects & Portfolio</span>
        <span class="chip" onclick="sendMessage('Tell me about Sparrow Interactive')">Company Info</span>
        <span class="chip" onclick="sendMessage('How can I contact Sparrow Interactive?')">Get in Touch</span>
        <span class="chip chip-report" onclick="startReportIssue()">Report an Issue</span>
    </div>
    <div class="welcome-search">
        <div class="input-wrapper">
            <input type="text" id="welcomeInput" placeholder="Ask me anything about Sparrow Interactive...">
            <button id="welcomeMicBtn" class="mic-btn" title="Click to speak">
                <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                    <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
                    <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
                </svg>
            </button>
            <button id="welcomeSendBtn" title="Send">
                <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                    <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                </svg>
            </button>
        </div>
    </div>
    <div class="suggested-questions">
        <p class="suggested-label">Popular questions</p>
        <div class="suggested-list" id="initialSuggestions">
        </div>
    </div>
</div>`;

// Logo click — soft reset to welcome state (no page reload)
document.getElementById("logoBtn").addEventListener("click", () => {
    stopSpeech();
    if (welcomeTypingTimer) clearTimeout(welcomeTypingTimer);
    // Generate a brand-new session ID so feedback doesn't carry over
    sessionId = "s_" + Math.random().toString(36).slice(2, 10) + Date.now().toString(36);
    conversationHistory = [];
    botMessageIndex = 0;
    reportIssueMode = false;
    welcomeTyped = false;
    messagesEl.innerHTML = welcomeCardHTML;
    document.getElementById("inputArea").style.display = "none";
    bindWelcomeInputListeners();
    typeWelcomeText();
    loadInitialSuggestions();
    const wi = document.getElementById("welcomeInput");
    if (wi) wi.focus();
});

// Start report issue flow
function startReportIssue() {
    // Remove welcome card and show footer input
    const welcomeCard = document.querySelector(".welcome-card");
    if (welcomeCard) {
        welcomeCard.remove();
        document.getElementById("inputArea").style.display = "";
        userInput.focus();
    }

    reportIssueMode = true;
    addMessage("Please describe the issue you're experiencing, and we'll look into it right away.", "bot");
    userInput.placeholder = "Describe your issue...";
    userInput.focus();
}

// Send message (can be called with a preset text for option clicks)
async function sendMessage(presetText) {
    stopSpeech();
    const rawText = (typeof presetText === "string" ? presetText : "") || userInput.value || "";
    const text = rawText.trim();

    // Empty or whitespace-only input — show a helpful nudge
    if (!text) {
        if (rawText.length > 0) {
            // User typed spaces and hit send
            userInput.value = "";
            const welcomeCard = document.querySelector(".welcome-card");
            if (welcomeCard) {
                welcomeCard.remove();
                document.getElementById("inputArea").style.display = "";
                userInput.focus();
            }
            addMessage("Please type a valid question. For example, try asking about our services, projects, or team.", "bot");
        }
        return;
    }

    // Remove welcome card and show footer input
    const welcomeCard = document.querySelector(".welcome-card");
    if (welcomeCard) {
        welcomeCard.remove();
        document.getElementById("inputArea").style.display = "";
        userInput.focus();
    }

    addMessage(text, "user");
    userInput.value = "";
    userInput.style.height = "auto";
    sendBtn.disabled = true;

    // Handle report issue mode
    if (reportIssueMode) {
        reportIssueMode = false;
        userInput.placeholder = "Ask me anything about Sparrow Interactive...";
        const typingEl = addTypingIndicator();
        try {
            const res = await fetch("/report-issue", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    session_id: sessionId,
                    message: text,
                    page_url: window.location.pathname,
                }),
            });
            typingEl.remove();
            if (res.ok) {
                addMessage("Thank you for reporting this issue. Our team will look into it right away.", "bot");
            } else {
                const errData = await res.json().catch(() => ({}));
                addMessage("Sorry, we couldn't submit your report. Please try again. " + (errData.detail || ""), "bot");
            }
        } catch (err) {
            typingEl.remove();
            addMessage("Error submitting report: " + err.message, "bot");
        } finally {
            sendBtn.disabled = false;
            userInput.focus();
        }
        return;
    }

    // Add to conversation history
    conversationHistory.push({ role: "user", content: text });

    const typingEl = addTypingIndicator();

    try {
        const res = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message: text,
                session_id: sessionId,
                history: conversationHistory.slice(0, -1).slice(-MAX_HISTORY),
                page_url: window.location.pathname,
            }),
        });

        if (!res.ok) {
            const errText = await res.text();
            try { throw new Error(JSON.parse(errText).detail || errText); }
            catch (e) { if (e instanceof SyntaxError) throw new Error(errText); throw e; }
        }

        const data = await res.json();
        typingEl.remove();

        if (data.needs_clarification) {
            addBotMessage(data.answer, data.sources, true, data.options || [], []);
        } else {
            addBotMessage(data.answer, data.sources, false, [], data.suggestions || []);
        }

        // Show follow-up message as a separate bubble after a short delay
        if (data.follow_up_message) {
            const followUpText = data.follow_up_message;
            setTimeout(() => {
                addMessage(followUpText, "bot");
            }, 800);
        }

        // Add assistant response to history (include follow-up so context is preserved)
        const fullAnswer = data.follow_up_message
            ? data.answer + "\n\n" + data.follow_up_message
            : data.answer;
        conversationHistory.push({ role: "assistant", content: fullAnswer });

        // Cap history length
        if (conversationHistory.length > MAX_HISTORY) {
            conversationHistory = conversationHistory.slice(-MAX_HISTORY);
        }

    } catch (err) {
        typingEl.remove();
        addMessage("Error: " + err.message, "bot");
    } finally {
        sendBtn.disabled = false;
        userInput.focus();
    }
}

// Handle option button click
window.handleOptionClick = function(optionText) {
    trackEvent("suggestion_clicked", { suggestion: optionText });
    sendMessage(optionText);
};

// Handle website scrape
// --- Feedback helpers ---
const THUMB_UP_SVG = `<svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M1 21h4V9H1v12zm22-11c0-1.1-.9-2-2-2h-6.31l.95-4.57.03-.32c0-.41-.17-.79-.44-1.06L14.17 1 7.59 7.59C7.22 7.95 7 8.45 7 9v10c0 1.1.9 2 2 2h9c.83 0 1.54-.5 1.84-1.22l3.02-7.05c.09-.23.14-.47.14-.73v-2z"/></svg>`;
const THUMB_DOWN_SVG = `<svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M15 3H6c-.83 0-1.54.5-1.84 1.22l-3.02 7.05c-.09.23-.14.47-.14.73v2c0 1.1.9 2 2 2h6.31l-.95 4.57-.03.32c0 .41.17.79.44 1.06L9.83 23l6.59-6.59c.36-.36.58-.86.58-1.41V5c0-1.1-.9-2-2-2zm4 0v12h4V3h-4z"/></svg>`;

function sendFeedback(msgIndex, feedback) {
    fetch("/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            session_id: sessionId,
            message_index: msgIndex,
            feedback: feedback,
        }),
    }).catch(() => {});
}

function createFeedbackButtons(msgIndex) {
    const upBtn = document.createElement("button");
    upBtn.className = "feedback-btn feedback-up";
    upBtn.title = "Good response";
    upBtn.innerHTML = THUMB_UP_SVG;

    const downBtn = document.createElement("button");
    downBtn.className = "feedback-btn feedback-down";
    downBtn.title = "Poor response";
    downBtn.innerHTML = THUMB_DOWN_SVG;

    upBtn.addEventListener("click", () => {
        const wasActive = upBtn.classList.contains("active");
        upBtn.classList.toggle("active");
        downBtn.classList.remove("active");
        if (!wasActive) sendFeedback(msgIndex, "up");
    });

    downBtn.addEventListener("click", () => {
        const wasActive = downBtn.classList.contains("active");
        downBtn.classList.toggle("active");
        upBtn.classList.remove("active");
        if (!wasActive) sendFeedback(msgIndex, "down");
    });

    return [upBtn, downBtn];
}

// Add a plain text message
function addMessage(text, role) {
    const div = document.createElement("div");
    div.className = `message ${role}`;

    let inner = "";
    if (role === "bot") {
        inner = `<div class="message-content"><div class="bot-label">SPARROWI</div><p>${escapeHtml(text)}</p>
            <div class="message-actions">
                <button class="tts-btn" title="Read aloud">
                    <svg class="tts-icon-speak" viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/></svg>
                    <svg class="tts-icon-stop" viewBox="0 0 24 24" width="14" height="14" fill="currentColor" style="display:none"><path d="M6 6h12v12H6z"/></svg>
                </button>
            </div>
        </div>`;
    } else {
        inner = `<div class="message-content"><p>${escapeHtml(text)}</p></div>`;
    }
    div.innerHTML = inner;

    // Attach TTS click handler + feedback buttons
    if (role === "bot") {
        const ttsBtn = div.querySelector(".tts-btn");
        if (ttsBtn) ttsBtn.addEventListener("click", () => speakText(text, ttsBtn));

        const actionsRow = div.querySelector(".message-actions");
        if (actionsRow) {
            const [upBtn, downBtn] = createFeedbackButtons(botMessageIndex);
            actionsRow.appendChild(upBtn);
            actionsRow.appendChild(downBtn);
            botMessageIndex++;
        }
    }

    messagesEl.appendChild(div);
    if (role === "bot") {
        scrollToMessageTop(div);
    } else {
        scrollToBottom();
    }
    return div;
}

// Add bot message with optional sources, clarification, options, and suggestions
function addBotMessage(answer, sources, isClarification, options, suggestions) {
    const div = document.createElement("div");
    div.className = "message bot";

    let html = `<div class="message-content">`;
    html += `<div class="bot-label">SPARROWI</div>${renderMarkdown(answer)}`;

    // Render clickable option buttons (clarification)
    if (isClarification && options && options.length > 0) {
        html += `<div class="options-container">`;
        for (const opt of options) {
            html += `<button class="option-btn" onclick="handleOptionClick('${escapeAttr(opt)}')">${escapeHtml(opt)}</button>`;
        }
        html += `</div>`;
    }

    // Render follow-up suggestions
    if (!isClarification && suggestions && suggestions.length > 0) {
        html += `<div class="suggestions-container">`;
        html += `<div class="suggestions-label">You might also want to ask:</div>`;
        for (const s of suggestions) {
            html += `<button class="suggestion-btn" onclick="handleOptionClick('${escapeAttr(s)}')">${escapeHtml(s)}</button>`;
        }
        html += `</div>`;
    }

    // Message actions row (TTS + sources)
    html += `<div class="message-actions">`;
    html += `<button class="tts-btn" title="Read aloud">
        <svg class="tts-icon-speak" viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/></svg>
        <svg class="tts-icon-stop" viewBox="0 0 24 24" width="14" height="14" fill="currentColor" style="display:none"><path d="M6 6h12v12H6z"/></svg>
    </button>`;

    if (sources && sources.length > 0) {
        const sourcesId = "sources-" + Date.now();
        html += `
            <button class="sources-btn" onclick="toggleSources('${sourcesId}')">
                Sources (${sources.length})
            </button>`;
        // Close message-actions, then add sources list outside
        html += `</div>`;
        html += `
            <div class="sources-toggle">
                <div class="sources-list" id="${sourcesId}">
                    ${sources.map(s => `
                        <div class="source-item">
                            <div class="source-meta">${escapeHtml(s.table)} / ${escapeHtml(s.chunk_type)}</div>
                            <pre>${escapeHtml(s.text)}</pre>
                        </div>
                    `).join("")}
                </div>
            </div>`;
    } else {
        html += `</div>`;
    }

    html += `</div>`;
    div.innerHTML = html;

    // Attach TTS click handler using data from the answer text
    const ttsBtn = div.querySelector(".tts-btn");
    if (ttsBtn) {
        const plainText = stripHtml(renderMarkdown(answer));
        ttsBtn.addEventListener("click", () => speakText(plainText, ttsBtn));
    }

    // Attach feedback buttons
    const actionsRow = div.querySelector(".message-actions");
    if (actionsRow) {
        const [upBtn, downBtn] = createFeedbackButtons(botMessageIndex);
        actionsRow.appendChild(upBtn);
        actionsRow.appendChild(downBtn);
        botMessageIndex++;
    }

    messagesEl.appendChild(div);
    scrollToMessageTop(div);
}

// Toggle sources visibility
window.toggleSources = function(id) {
    const el = document.getElementById(id);
    if (el) el.classList.toggle("show");
};

// Add typing indicator
function addTypingIndicator() {
    const div = document.createElement("div");
    div.className = "message bot";
    div.innerHTML = `
        <div class="message-content">
            <div class="bot-label">SPARROWI</div>
            <div class="typing-indicator">
                <span></span><span></span><span></span>
            </div>
        </div>`;
    messagesEl.appendChild(div);
    scrollToBottom();
    return div;
}

// Scroll to bottom (for user messages, typing indicator, etc.)
function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
}

// Scroll so the top of a given element is visible in the messages container
function scrollToMessageTop(el) {
    if (!el) return;
    const containerRect = messagesEl.getBoundingClientRect();
    const elRect = el.getBoundingClientRect();
    const offset = elRect.top - containerRect.top + messagesEl.scrollTop;
    // Small padding (8px) so the message isn't glued to the very top
    messagesEl.scrollTo({ top: offset - 8, behavior: "smooth" });
}

// Simple markdown rendering
function renderMarkdown(text) {
    // Strip ALL characters known to cause broken-image icons on Windows:
    // - U+FE0E/U+FE0F: variation selectors (force image presentation)
    // - U+FFFC/U+FFFD: object replacement / replacement character
    // - U+200B-U+200F: zero-width spaces/joiners/marks
    // - U+202A-U+202E: bidirectional formatting
    // - U+2060-U+2069: invisible formatters
    // - U+E0001-U+E007F: tags block (emoji flag sequences)
    text = text.replace(/[\uFE0E\uFE0F\uFFFC\uFFFD\u200B-\u200F\u202A-\u202E\u2060-\u2069]/g, "");
    // Also strip surrogate-based tag characters and skin tone modifiers that cause double rendering
    text = text.replace(/[\u{E0001}-\u{E007F}\u{1F3FB}-\u{1F3FF}]/gu, "");

    // Extract markdown links before escaping: [text](url)
    const links = [];
    text = text.replace(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g, (_, linkText, url) => {
        const placeholder = `__LINK_${links.length}__`;
        links.push({ text: linkText, url: url });
        return placeholder;
    });

    let html = escapeHtml(text);

    // Restore links as clickable <a> tags
    links.forEach((link, i) => {
        html = html.replace(
            `__LINK_${i}__`,
            `<a href="${escapeHtml(link.url)}" target="_blank" rel="noopener" class="chat-link">${escapeHtml(link.text)}</a>`
        );
    });

    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
    html = html.replace(/^## (.*?)$/gm, "<strong style='font-size:14px'>$1</strong>");
    html = html.split("\n\n").map(p => `<p>${p}</p>`).join("");
    html = html.replace(/\n/g, "<br>");
    html = html.replace(/<br>- (.*?)(?=<br>|<\/p>)/g, "</p><ul><li>$1</li></ul><p>");
    html = html.replace(/<\/ul><p><\/p><ul>/g, "");
    html = html.replace(/<\/ul><p>(<br>)?<\/p><ul>/g, "");
    return html;
}

// Escape HTML
function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

// Escape for use inside HTML attributes (onclick)
function escapeAttr(text) {
    return text.replace(/'/g, "\\'").replace(/"/g, "&quot;");
}

// --- Speech-to-Text (Mic Recording via Sarvam AI) ---
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let recordingMimeType = "audio/webm";

// Detect best supported mimeType
function getSupportedMimeType() {
    const types = [
        "audio/webm;codecs=opus",
        "audio/webm",
        "audio/ogg;codecs=opus",
        "audio/mp4",
        "audio/wav",
    ];
    for (const type of types) {
        if (typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported(type)) {
            return type;
        }
    }
    return "";
}

async function startRecording(micBtn) {
    // Check browser support
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        addMessage("Your browser does not support microphone access. Please use Chrome, Edge, or Firefox.", "bot");
        return;
    }
    if (typeof MediaRecorder === "undefined") {
        addMessage("Your browser does not support audio recording. Please use Chrome, Edge, or Firefox.", "bot");
        return;
    }

    const mimeType = getSupportedMimeType();
    if (!mimeType) {
        addMessage("No supported audio format found in your browser.", "bot");
        return;
    }
    recordingMimeType = mimeType;

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

        try {
            mediaRecorder = new MediaRecorder(stream, { mimeType: mimeType });
        } catch (e) {
            // Fallback: let browser choose default
            mediaRecorder = new MediaRecorder(stream);
        }

        audioChunks = [];

        mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) audioChunks.push(e.data);
        };

        mediaRecorder.onstop = async () => {
            stream.getTracks().forEach(t => t.stop());
            const blobType = mediaRecorder.mimeType || recordingMimeType;
            const audioBlob = new Blob(audioChunks, { type: blobType });
            micBtn.classList.remove("recording");
            micBtn.title = "Click to speak";
            isRecording = false;
            await transcribeAudio(audioBlob, blobType);
        };

        mediaRecorder.onerror = (e) => {
            console.error("[Mic] MediaRecorder error:", e);
            stream.getTracks().forEach(t => t.stop());
            micBtn.classList.remove("recording");
            micBtn.title = "Click to speak";
            isRecording = false;
            addMessage("Recording failed. Please try again.", "bot");
        };

        mediaRecorder.start();
        isRecording = true;
        micBtn.classList.add("recording");
        micBtn.title = "Recording... click to stop";
    } catch (err) {
        console.error("[Mic] getUserMedia error:", err);
        if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
            addMessage("Microphone access denied. Please allow mic permission in your browser settings.", "bot");
        } else {
            addMessage("Could not access microphone: " + err.message, "bot");
        }
    }
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state === "recording") {
        mediaRecorder.stop();
    }
}

async function transcribeAudio(audioBlob, mimeType) {
    // Remove welcome card and show footer input if needed
    const welcomeCard = document.querySelector(".welcome-card");
    if (welcomeCard) {
        welcomeCard.remove();
        document.getElementById("inputArea").style.display = "";
        userInput.focus();
    }

    const typingEl = addTypingIndicator();

    // Determine file extension from mimeType
    let ext = "webm";
    if (mimeType && mimeType.includes("ogg")) ext = "ogg";
    else if (mimeType && mimeType.includes("mp4")) ext = "mp4";
    else if (mimeType && mimeType.includes("wav")) ext = "wav";

    try {
        const formData = new FormData();
        formData.append("file", audioBlob, "recording." + ext);

        const res = await fetch("/transcribe", {
            method: "POST",
            body: formData,
        });

        if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData.detail || "Transcription failed");
        }

        const data = await res.json();
        typingEl.remove();

        if (data.transcript && data.transcript.trim()) {
            sendMessage(data.transcript.trim());
        } else {
            addMessage("Sorry, I couldn't understand the audio. Please try again.", "bot");
        }
    } catch (err) {
        typingEl.remove();
        addMessage("Transcription error: " + err.message, "bot");
    }
}

function bindMicButton(btn) {
    if (!btn) return;
    btn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (isRecording) {
            stopRecording();
        } else {
            startRecording(btn);
        }
    });
}

bindMicButton(document.getElementById("micBtn"));
bindMicButton(document.getElementById("welcomeMicBtn"));
