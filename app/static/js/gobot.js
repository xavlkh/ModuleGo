/**
 * GoBot chatbot: AI-powered module recommendation advisor.
 * Handles chat UI, message history, and server communication.
 * @module gobot
 */
const GoBot = {
  STORAGE_KEY: 'gobot_history',
  WELCOME_KEY: 'gobot_welcomed',
  MAX_HISTORY: 50,

  get hasPopped() {
    return localStorage.getItem(this.WELCOME_KEY) === 'true';
  },

  init() {
    const botHTML = `
      <div id="gobot-btn" class="fixed bottom-5 right-5 z-[9999] hidden h-12 w-12 cursor-pointer items-center justify-center rounded-full bg-primary-500 text-white shadow-lg hover:bg-primary-600 transition-all" style="display:none">
        <i data-lucide="bot" class="h-6 w-6"></i>
      </div>

      <div id="gobot-welcome" class="fixed bottom-[90px] right-5 z-[10000] hidden w-[320px] rounded-2xl bg-white dark:bg-[var(--dark-bg-elevated)] dark:border dark:border-[var(--dark-border)] p-5 shadow-2xl" style="display:none">
        <div class="flex gap-3">
          <div class="flex h-10 w-10 items-center justify-center rounded-full bg-primary-500 text-white shrink-0">
            <i data-lucide="bot" class="h-5 w-5"></i>
          </div>
          <div class="flex-1 min-w-0">
            <b class="text-zinc-900 dark:text-[var(--dark-text)]">Hi, I'm GoBot!</b>
            <p class="my-2 text-sm leading-relaxed text-zinc-500 dark:text-[var(--dark-text-muted)]">Tell me your career goals or interests, and I'll recommend the perfect modules for you.</p>
            <div class="flex flex-wrap gap-2">
              <button class="gobot-quick rounded-full border border-zinc-200 dark:border-[var(--dark-border)] bg-zinc-50 dark:bg-[var(--dark-bg)] px-2.5 py-1.5 text-xs text-zinc-700 dark:text-[var(--dark-text)] hover:bg-zinc-100 dark:hover:bg-[var(--dark-bg-elevated)] transition-colors" data-msg="What modules for UI/UX Designer?">UI/UX Designer</button>
              <button class="gobot-quick rounded-full border border-zinc-200 dark:border-[var(--dark-border)] bg-zinc-50 dark:bg-[var(--dark-bg)] px-2.5 py-1.5 text-xs text-zinc-700 dark:text-[var(--dark-text)] hover:bg-zinc-100 dark:hover:bg-[var(--dark-bg-elevated)] transition-colors" data-msg="What modules for Data Analyst?">Data Analyst</button>
              <button class="gobot-quick rounded-full border border-zinc-200 dark:border-[var(--dark-border)] bg-zinc-50 dark:bg-[var(--dark-bg)] px-2.5 py-1.5 text-xs text-zinc-700 dark:text-[var(--dark-text)] hover:bg-zinc-100 dark:hover:bg-[var(--dark-bg-elevated)] transition-colors" data-msg="I like coding and building apps">I like coding</button>
            </div>
            <div class="mt-3 flex flex-col gap-2">
              <button id="gobot-yes" class="w-full rounded-lg bg-primary-500 px-3 py-2 text-sm font-semibold text-white hover:bg-primary-600 transition-colors">Help me find modules</button>
              <button id="gobot-no" class="w-full rounded-lg border border-zinc-400 dark:border-[var(--dark-border-subtle)] bg-zinc-100 dark:bg-[var(--dark-bg-elevated)] px-3 py-2 text-sm font-medium text-zinc-700 dark:text-[var(--dark-text)] hover:bg-zinc-200 dark:hover:bg-[var(--dark-border)] transition-colors">Later</button>
            </div>
            <button id="gobot-welcome-close" class="absolute right-3 top-3 text-zinc-400 hover:text-zinc-600 dark:hover:text-[var(--dark-text)] transition-colors" aria-label="Close"><i data-lucide="x" class="h-4 w-4"></i></button>
          </div>
        </div>
      </div>

      <div id="gobot-chat" class="fixed bottom-[90px] right-5 z-[9999] hidden h-[480px] w-[350px] flex-col rounded-xl bg-white dark:bg-[var(--dark-bg)] dark:border dark:border-[var(--dark-border)] shadow-2xl" style="display:none">
        <div class="flex items-center justify-between rounded-t-xl bg-primary-500 px-4 py-3 text-white shrink-0">
          <div class="flex items-center gap-2">
            <i data-lucide="bot" class="h-5 w-5"></i>
            <span class="font-semibold text-sm">GoBot</span>
          </div>
          <div class="flex items-center gap-3">
            <button id="gobot-clear" class="text-xs text-white/80 hover:text-white transition-colors">Clear</button>
            <button id="gobot-close" class="text-white/80 hover:text-white transition-colors" aria-label="Close chat"><i data-lucide="x" class="h-4 w-4"></i></button>
          </div>
        </div>
        <div id="gobot-messages" class="flex-1 overflow-y-auto p-4 space-y-3"></div>
        <div id="gobot-typing" class="hidden px-4 pb-1 text-xs text-zinc-400 dark:text-[var(--dark-text-muted)]">
          <span class="gobot-dot-anim">GoBot is thinking</span>
        </div>
        <div class="flex flex-wrap gap-1.5 border-t border-zinc-100 dark:border-[var(--dark-border)] px-3 py-2 shrink-0">
          <button class="gobot-quick rounded-full border border-zinc-200 dark:border-[var(--dark-border)] bg-zinc-50 dark:bg-[var(--dark-bg)] px-2 py-1 text-[11px] text-zinc-600 dark:text-[var(--dark-text-muted)] hover:bg-zinc-100 dark:hover:bg-[var(--dark-bg-elevated)] transition-colors" data-msg="What modules for Data Analyst?">Data Analyst</button>
          <button class="gobot-quick rounded-full border border-zinc-200 dark:border-[var(--dark-border)] bg-zinc-50 dark:bg-[var(--dark-bg)] px-2 py-1 text-[11px] text-zinc-600 dark:text-[var(--dark-text-muted)] hover:bg-zinc-100 dark:hover:bg-[var(--dark-bg-elevated)] transition-colors" data-msg="What modules for UI/UX Designer?">UI/UX</button>
          <button class="gobot-quick rounded-full border border-zinc-200 dark:border-[var(--dark-border)] bg-zinc-50 dark:bg-[var(--dark-bg)] px-2 py-1 text-[11px] text-zinc-600 dark:text-[var(--dark-text-muted)] hover:bg-zinc-100 dark:hover:bg-[var(--dark-bg-elevated)] transition-colors" data-msg="I like cybersecurity">Cybersecurity</button>
        </div>
        <div class="flex gap-2 border-t border-zinc-200 dark:border-[var(--dark-border)] p-3 shrink-0">
          <input id="gobot-input" placeholder="Describe your dream career..." class="flex-1 rounded-lg border border-zinc-300 dark:border-[var(--dark-border-subtle)] bg-white dark:bg-[var(--dark-bg)] px-3 py-2 text-sm text-zinc-900 dark:text-[var(--dark-text)] placeholder-zinc-400 dark:placeholder-[var(--dark-text-muted)] focus:outline-none focus:ring-2 focus:ring-primary-400/50 disabled:opacity-50">
          <button id="gobot-send" class="rounded-lg bg-primary-500 px-3 py-2 text-white hover:bg-primary-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"><i data-lucide="send" class="h-4 w-4"></i></button>
        </div>
      </div>
    `;
    document.body.insertAdjacentHTML('beforeend', botHTML);
    if (typeof lucide !== 'undefined') lucide.createIcons();

    document.getElementById('gobot-btn').onclick = () => this.openChat();
    document.getElementById('gobot-close').onclick = () => this.closeChat();
    document.getElementById('gobot-clear').onclick = () => this.clearHistory();
    document.getElementById('gobot-welcome-close').onclick = () => this.dismissWelcome();
    document.getElementById('gobot-no').onclick = () => this.dismissWelcome();
    document.getElementById('gobot-yes').onclick = () => this.acceptHelp();
    document.getElementById('gobot-send').onclick = () => this.send();
    document.getElementById('gobot-input').onkeydown = (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); this.send(); } };
    document.querySelectorAll('.gobot-quick').forEach(btn => {
      btn.onclick = (e) => this.quickSend(e.currentTarget.dataset.msg);
    });

    this.loadHistory();
    // First-time visitors: show welcome popup after 1s (lets page load animations finish).
    // Returning visitors (localStorage flag set): show bot button immediately.
    if (this.hasPopped) {
        this.showButton();
    } else {
        setTimeout(() => this.showWelcome(), 1000);
    }
  },

  showButton() {
    const btn = document.getElementById('gobot-btn');
    if (btn) btn.style.display = 'flex';
  },

  getHistory() {
    try {
      return JSON.parse(localStorage.getItem(this.STORAGE_KEY) || '[]');
    } catch { return []; }
  },

  pushHistory(role, text, links, suggestions) {
    const msgs = this.getHistory();
    msgs.push({ role, text, links: links || [], suggestions: suggestions || [], ts: Date.now() });
    localStorage.setItem(this.STORAGE_KEY, JSON.stringify(msgs.slice(-this.MAX_HISTORY)));
  },

  loadHistory() {
    const msgs = this.getHistory();
    const box = document.getElementById('gobot-messages');
    if (!box) return;
    box.innerHTML = '';
    msgs.forEach(m => {
      if (m.role === 'bot') {
        this.renderBotMessage(m.text, m.links || [], m.suggestions || []);
      } else {
        this.renderUserMessage(m.text);
      }
    });
    box.scrollTop = box.scrollHeight;
  },

  clearHistory() {
    if (!window.confirm('Clear chat history?')) return;
    localStorage.removeItem(this.STORAGE_KEY);
    const box = document.getElementById('gobot-messages');
    if (box) box.innerHTML = '';
    this.pushHistory('bot', 'History cleared! Ready to find your ideal modules?');
    this.renderBotMessage('History cleared! Ready to find your ideal modules?', [], ['I like programming', 'What modules for Data Analyst?']);
  },

  quickSend(msg) {
    this.openChat();
    const input = document.getElementById('gobot-input');
    if (input) input.value = msg;
    this.send();
  },

  showWelcome() {
    const el = document.getElementById('gobot-welcome');
    if (el) el.style.display = 'block';
  },

  dismissWelcome() {
    const welcome = document.getElementById('gobot-welcome');
    if (welcome) welcome.style.display = 'none';
    this.showButton();
    localStorage.setItem(this.WELCOME_KEY, 'true');
  },

  acceptHelp() {
    const welcome = document.getElementById('gobot-welcome');
    if (welcome) welcome.style.display = 'none';
    this.openChat();
    localStorage.setItem(this.WELCOME_KEY, 'true');
  },

  openChat() {
    const chat = document.getElementById('gobot-chat');
    const btn = document.getElementById('gobot-btn');
    const welcome = document.getElementById('gobot-welcome');
    if (chat) chat.style.display = 'flex';
    if (btn) btn.style.display = 'none';
    if (welcome) welcome.style.display = 'none';
    const history = this.getHistory();
    if (history.length === 0) {
      this.renderBotMessage("Hi! What career are you exploring?\n\nTell me your interests or goals, and I'll recommend modules for you.", [], ['I like designing websites', 'I want to be a Data Analyst', 'What is ModuleGo?']);
    }
    setTimeout(() => {
      const input = document.getElementById('gobot-input');
      if (input) input.focus();
      const box = document.getElementById('gobot-messages');
      if (box) box.scrollTop = box.scrollHeight;
    }, 100);
  },

  closeChat() {
    const chat = document.getElementById('gobot-chat');
    if (chat) chat.style.display = 'none';
    this.showButton();
  },

  renderUserMessage(text) {
    const box = document.getElementById('gobot-messages');
    if (!box) return;
    const div = document.createElement('div');
    div.className = 'max-w-[80%] rounded-xl px-3 py-2 text-sm leading-relaxed bg-primary-500 text-white self-end ml-auto';
    div.textContent = text;
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
  },

  renderBotMessage(text, links = [], suggestions = []) {
    const box = document.getElementById('gobot-messages');
    if (!box) return;
    const div = document.createElement('div');
    div.className = 'max-w-[85%] rounded-xl px-3 py-2 text-sm leading-relaxed whitespace-pre-wrap bg-zinc-100 dark:bg-[var(--dark-bg-elevated)] dark:border dark:border-[var(--dark-border)] text-zinc-800 dark:text-[var(--dark-text)] self-start';
    const p = document.createElement('p');
    p.textContent = text;
    div.appendChild(p);
    if (links.length) {
      const linkDiv = document.createElement('div');
      linkDiv.className = 'mt-2 space-y-1';
      links.forEach(l => {
        const a = document.createElement('a');
        a.href = l.url;
        a.className = 'block text-primary-600 dark:text-[var(--color-primary-400)] hover:underline text-xs font-medium';
        a.textContent = l.text;
        a.target = '_blank';
        linkDiv.appendChild(a);
      });
      div.appendChild(linkDiv);
    }
    if (suggestions.length) {
      const chipDiv = document.createElement('div');
      chipDiv.className = 'mt-2 flex flex-wrap gap-1.5';
      suggestions.forEach(s => {
        const chip = document.createElement('button');
        chip.className = 'rounded-full border border-primary-200 dark:border-[oklch(0.3_0.04_150)] bg-primary-50 dark:bg-[oklch(0.2_0.015_150)] px-2.5 py-1 text-[11px] text-primary-700 dark:text-[oklch(0.85_0.06_150)] hover:bg-primary-100 dark:hover:bg-[oklch(0.25_0.02_150)] transition-colors cursor-pointer';
        chip.textContent = s;
        chip.onclick = () => this.quickSend(s);
        chipDiv.appendChild(chip);
      });
      div.appendChild(chipDiv);
    }
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
  },

  setLoading(loading) {
    const input = document.getElementById('gobot-input');
    const send = document.getElementById('gobot-send');
    const typing = document.getElementById('gobot-typing');
    if (input) input.disabled = loading;
    if (send) send.disabled = loading;
    if (typing) typing.classList.toggle('hidden', !loading);
  },

  async send() {
    const input = document.getElementById('gobot-input');
    if (!input) return;
    const msg = input.value.trim();
    if (!msg) return;

    this.renderUserMessage(msg);
    this.pushHistory('user', msg);
    input.value = '';
    this.setLoading(true);

    const history = this.getHistory().slice(-10).map(m => ({ role: m.role, text: m.text }));

    try {
      const controller = new AbortController();
      // 30-second timeout prevents hung requests from blocking the UI
      const timeout = setTimeout(() => controller.abort(), 30000);
      const res = await fetch('/api/gobot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg, history }),
        signal: controller.signal,
      });
      clearTimeout(timeout);

      if (!res.ok) throw new Error(`Server error (${res.status})`);

      const data = await res.json();
      const reply = data.reply || "Sorry, I didn't understand that.";
      const links = data.links || [];
      const suggestions = data.suggestions || [];

      this.renderBotMessage(reply, links, suggestions);
      this.pushHistory('bot', reply, links, suggestions);
    } catch (err) {
      if (err.name === 'AbortError') {
        this.renderBotMessage("Sorry, I took too long to respond. Please try again.");
      } else {
        this.renderBotMessage("Oops! Something went wrong. Please check your connection and try again.");
      }
    } finally {
      this.setLoading(false);
    }
  },
};

document.addEventListener('DOMContentLoaded', () => GoBot.init());
