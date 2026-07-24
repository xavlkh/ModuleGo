const GoBot = {
  STORAGE_KEY: 'gobot_history',
  hasPopped: localStorage.getItem('gobot_welcomed') === 'true',

  init() {
    const botHTML = `
      <div id="gobot-btn" style="position:fixed;bottom:20px;right:20px;width:60px;height:60px;background:#5b4eff;border-radius:50%;display:flex;align-items:center;justify-content:center;cursor:pointer;z-index:9999;box-shadow:0 4px 12px rgba(0,0,0,0.2);display:none">🤖</div>
      
      <div id="gobot-welcome" style="display:none;position:fixed;bottom:90px;right:20px;width:320px;background:white;border-radius:16px;box-shadow:0 8px 24px rgba(0,0,0,0.2);z-index:10000;padding:20px;">
        <div style="display:flex;gap:12px;">
          <div style="width:40px;height:40px;background:#5b4eff;border-radius:50%;display:flex;align-items:center;justify-content:center;">🤖</div>
          <div style="flex:1">
            <b>Hi, I'm GoBot!</b>
            <p style="margin:8px 0 12px;font-size:14px;color:#555;line-height:1.4">New here? I can help you find modules for your dream career or show you around.</p>
            <div style="display:flex;gap:8px;flex-wrap:wrap">
              <button class="gobot-quick" data-msg="What modules for UI/UX Designer?" style="padding:6px 10px;background:#f5f3ff;border:1px solid #ddd;border-radius:20px;font-size:12px;cursor:pointer;">🎨 UI/UX</button>
              <button class="gobot-quick" data-msg="What modules for Data Analyst?" style="padding:6px 10px;background:#f5f3ff;border:1px solid #ddd;border-radius:20px;font-size:12px;cursor:pointer;">📊 Data Analyst</button>
              <button class="gobot-quick" data-msg="How to use ModuleGo?" style="padding:6px 10px;background:#f5f3ff;border:1px solid #ddd;border-radius:20px;font-size:12px;cursor:pointer;">🧭 Guide me</button>
            </div>
            <div style="display:flex;gap:8px;margin-top:12px;">
              <button id="gobot-yes" style="flex:1;padding:8px;background:#5b4eff;color:white;border:none;border-radius:8px;cursor:pointer;">Yes, help me</button>
              <button id="gobot-no" style="padding:8px 12px;background:#f1f1f1;border:none;border-radius:8px;cursor:pointer;">Later</button>
            </div>
          <span id="gobot-welcome-close" style="cursor:pointer;color:#999">✕</span>
        </div>
      </div>

      <div id="gobot-chat" style="display:none;position:fixed;bottom:90px;right:20px;width:350px;height:480px;background:white;border-radius:12px;box-shadow:0 8px 24px rgba(0,0,0,0.15);z-index:9999;flex-direction:column;">
        <div style="padding:16px;background:#5b4eff;color:white;border-radius:12px 12px 0 0;display:flex;justify-content:space-between;align-items:center;">
          <b>GoBot - Module Helper</b>
          <div style="display:flex;gap:12px;align-items:center">
            <span id="gobot-clear" style="font-size:12px;cursor:pointer;opacity:0.8">Clear</span>
            <span id="gobot-close" style="cursor:pointer">✕</span>
          </div>
        </div>
        <div id="gobot-messages" style="flex:1;overflow-y:auto;padding:16px;"></div>
        <div id="gobot-quick-row" style="padding:8px 12px;display:flex;gap:6px;flex-wrap:wrap;border-top:1px solid #f0f0f0;">
          <button class="gobot-quick" data-msg="What modules for Data Analyst?" style="padding:4px 8px;background:#f5f3ff;border:1px solid #e0e0e0;border-radius:16px;font-size:11px;cursor:pointer;">📊 Data Analyst</button>
          <button class="gobot-quick" data-msg="What modules for UI/UX Designer?" style="padding:4px 8px;background:#f5f3ff;border:1px solid #e0e0e0;border-radius:16px;font-size:11px;cursor:pointer;">🎨 UI/UX</button>
          <button class="gobot-quick" data-msg="Compare modules" style="padding:4px 8px;background:#f5f3ff;border:1px solid #e0e0e0;border-radius:16px;font-size:11px;cursor:pointer;">⚖️ Compare</button>
        </div>
        <div style="padding:12px;display:flex;gap:8px;border-top:1px solid #eee;">
          <input id="gobot-input" placeholder="Ask something..." style="flex:1;padding:8px;border:1px solid #ddd;border-radius:8px;">
          <button id="gobot-send" style="padding:8px 12px;background:#5b4eff;color:white;border:none;border-radius:8px;">Send</button>
        </div>
      </div>
    `;
    document.body.insertAdjacentHTML('beforeend', botHTML);

    // Events
    document.getElementById('gobot-btn').onclick = () => this.openChat();
    document.getElementById('gobot-close').onclick = () => this.closeChat();
    document.getElementById('gobot-clear').onclick = () => this.clearHistory();
    document.getElementById('gobot-welcome-close').onclick = () => this.dismissWelcome();
    document.getElementById('gobot-no').onclick = () => this.dismissWelcome();
    document.getElementById('gobot-yes').onclick = () => this.acceptHelp();
    document.getElementById('gobot-send').onclick = () => this.send();
    document.getElementById('gobot-input').onkeypress = (e) => { if(e.key==='Enter') this.send() };
    document.querySelectorAll('.gobot-quick').forEach(btn=>{
      btn.onclick = (e)=> this.quickSend(e.target.dataset.msg);
    });

    // Load history if exists
    this.loadHistory();

    setTimeout(() => {
      if (!this.hasPopped) this.showWelcome();
      else document.getElementById('gobot-btn').style.display = 'flex';
    }, 2000);
  },

  // --- HISTORY LOGIC ---
  saveHistory() {
    const msgs = document.getElementById('gobot-messages').innerHTML;
    localStorage.setItem(this.STORAGE_KEY, msgs);
  },
  loadHistory() {
    const saved = localStorage.getItem(this.STORAGE_KEY);
    if (saved) {
      document.getElementById('gobot-messages').innerHTML = saved;
      const box = document.getElementById('gobot-messages');
      box.scrollTop = box.scrollHeight;
    }
  },
  clearHistory() {
    if(confirm("Clear chat history?")){
      localStorage.removeItem(this.STORAGE_KEY);
      document.getElementById('gobot-messages').innerHTML = '';
      this.addMessage("bot", "History cleared! How can I help you now?");
    }
  },

  quickSend(msg){ 
    this.openChat(); 
    document.getElementById('gobot-input').value = msg;
    this.send();
  },
  showWelcome(){ document.getElementById('gobot-welcome').style.display='block'; },
  dismissWelcome(){
    document.getElementById('gobot-welcome').style.display='none';
    document.getElementById('gobot-btn').style.display='flex';
    localStorage.setItem('gobot_welcomed','true');
  },
  acceptHelp(){
    document.getElementById('gobot-welcome').style.display='none';
    this.openChat();
    localStorage.setItem('gobot_welcomed','true');
  },
  openChat(){
    document.getElementById('gobot-chat').style.display='flex';
    document.getElementById('gobot-btn').style.display='none';
    document.getElementById('gobot-welcome').style.display='none';
    if(!localStorage.getItem(this.STORAGE_KEY)){
      this.addMessage("bot", "Hi! 👋 What career are you exploring?\n\nClick a quick button or type your question.");
    }
  },
  closeChat(){
    document.getElementById('gobot-chat').style.display='none';
    document.getElementById('gobot-btn').style.display='flex';
  },
  addMessage(sender, text, links=[]) {
    const box = document.getElementById('gobot-messages');
    const div = document.createElement('div');
    div.style.marginBottom='12px'; div.style.padding='8px 12px'; div.style.borderRadius='12px'; div.style.maxWidth='80%'; div.style.whiteSpace='pre-line'; div.style.fontSize='14px';
    if(sender==='bot'){
      div.style.background='#f5f3ff';
      div.innerHTML = text.replace(/\n/g,'<br>') + (links.length ? '<br><br>' + links.map(l=>`<a href="${l.url}" style="color:#5b4eff;display:block;margin-top:4px">→ ${l.text}</a>`).join('') : '');
    } else {
      div.style.background='#5b4eff'; div.style.color='white'; div.style.marginLeft='auto'; div.textContent=text;
    }
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
    this.saveHistory(); // SAVE EVERY MESSAGE
  },
  async send() {
    const input = document.getElementById('gobot-input');
    const msg = input.value.trim();
    if(!msg) return;
    this.addMessage('user', msg);
    input.value = '';
    const res = await fetch('/api/gobot', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({message: msg})
    });
    const data = await res.json();
    this.addMessage('bot', data.reply, data.links||[]);
  }
};
document.addEventListener('DOMContentLoaded', ()=> GoBot.init());