const log = document.getElementById("log");
const form = document.getElementById("form");
const input = document.getElementById("input");
const sendBtn = document.getElementById("send");
const eraBtn = document.getElementById("eraBtn");
const titleEl = document.getElementById("title");
const titlebarEl = document.getElementById("titlebar");

// Her dönemin metinleri
const ERAS = {
  "1996": {
    pageTitle: "*** RetroBot 1996 - Hoş Geldiniz! ***",
    title: "~*~ RetroBot 1996 ~*~",
    titlebar: " RetroBot.exe - Sohbet Penceresi",
    placeholder: "Mesajınızı yazın...",
    send: "Gönder",
    toggle: "✨ Modernleştir",
    me: "Sen>",
    bot: "RetroBot>",
    sys: "***",
    wait: "Veri yükleniyor, lütfen bekleyin...",
    err: "HATA:",
    intro: [
      ["sys", "56K modem ile bağlanılıyor... bzzzt-kshhh-biiip... Bağlantı kuruldu!"],
      ["bot", "Selam! Ben RetroBot. Yıl 1996, internet harika değil mi? Sor bakalım!"],
    ],
  },
  "2030": {
    pageTitle: "RetroBot 2030",
    title: "RetroBot 2030",
    titlebar: "RetroBot AI • Canlı Sohbet",
    placeholder: "Bir şey sor...",
    send: "Gönder →",
    toggle: "⏪ Retro'ya Dön",
    me: "Sen",
    bot: "RetroBot",
    sys: "•",
    wait: "Düşünüyor...",
    err: "Hata:",
    intro: [
      ["sys", "Nöral bağlantı kuruldu • 5G+ • gecikme 1 ms"],
      ["bot", "Merhaba! Ben RetroBot, 2030'un sohbet asistanıyım. Uçan taksiler bile bu kadar hızlı değil. Ne öğrenmek istersin?"],
    ],
  },
};

let era = "1996";
let history = [];

// Sahte ziyaretçi sayacı
(function () {
  let n = Number(localStorage.getItem("visits") || 1337) + 1;
  localStorage.setItem("visits", n);
  document.getElementById("counter").textContent = String(n).padStart(6, "0");
})();

function addLine(cls, text) {
  const t = ERAS[era];
  const div = document.createElement("div");
  div.className = cls;
  const who = document.createElement("span");
  who.className = "who";
  who.textContent = t[cls === "me" ? "me" : cls === "bot" ? "bot" : "sys"] + " ";
  const body = document.createElement("span");
  body.textContent = text; // textContent: HTML enjekte edilemez
  div.append(who, body);
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
  return div;
}

function setEra(next) {
  era = next;
  const t = ERAS[era];
  document.body.classList.toggle("modern", era === "2030");
  document.title = t.pageTitle;
  titleEl.textContent = t.title;
  titlebarEl.textContent = t.titlebar;
  input.placeholder = t.placeholder;
  sendBtn.textContent = t.send;
  eraBtn.textContent = t.toggle;

  // Yeni dönem = yeni sohbet
  history = [];
  log.textContent = "";
  t.intro.forEach(([cls, text]) => addLine(cls, text));
  input.focus();
}

eraBtn.addEventListener("click", () => setEra(era === "1996" ? "2030" : "1996"));

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text) return;

  const currentEra = era;
  input.value = "";
  addLine("me", text);
  history.push({ role: "user", content: text });

  sendBtn.disabled = true;
  const wait = addLine("sys", ERAS[era].wait);

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: history, era: currentEra }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Bilinmeyen hata");
    if (currentEra !== era) return; // cevap beklenirken dönem değiştiyse at
    wait.remove();
    addLine("bot", data.reply);
    history.push({ role: "bot", content: data.reply });
  } catch (err) {
    if (currentEra !== era) return;
    wait.remove();
    history.pop(); // başarısız mesajı geçmişten çıkar
    addLine("sys", ERAS[era].err + " " + err.message);
  } finally {
    sendBtn.disabled = false;
    input.focus();
  }
});

setEra("1996");
