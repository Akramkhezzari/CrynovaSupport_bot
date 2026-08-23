const state = {
  user: { name: "عضو Crynova", id: "CRY-28419" },
  tickets: [
    {
      id: "CRY-1048",
      category: "مشكلة في السحب",
      status: "open",
      date: "23 أغسطس 2026",
      description: "طلب السحب مازال قيد المراجعة.",
      messages: [
        { from: "user", text: "طلب السحب مازال قيد المراجعة، هل يمكنكم التحقق؟", time: "14:12" },
        { from: "support", text: "أهلاً بك، تم استلام طلبك وسيقوم فريق الدعم بالتحقق منه.", time: "14:18" }
      ]
    },
    {
      id: "CRY-1032",
      category: "مشكلة في الإيداع",
      status: "closed",
      date: "21 أغسطس 2026",
      description: "تأخر ظهور الإيداع.",
      messages: [
        { from: "user", text: "قمت بالإيداع ولم يظهر في الحساب.", time: "09:30" },
        { from: "support", text: "تم التحقق من العملية وإضافة الرصيد إلى حسابك.", time: "09:44" }
      ]
    }
  ]
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

function saveState() {
  localStorage.setItem("crynova_support_tickets", JSON.stringify(state.tickets));
}

function loadState() {
  try {
    const saved = JSON.parse(localStorage.getItem("crynova_support_tickets"));
    if (Array.isArray(saved)) state.tickets = saved;
  } catch (_) {}
}

function statusText(status) {
  return { open: "قيد المراجعة", waiting: "بانتظار الرد", closed: "تم الحل" }[status] || "قيد المراجعة";
}

function renderTickets() {
  const list = $("#ticketList");
  $("#openTickets").textContent = state.tickets.filter(t => t.status !== "closed").length;

  if (!state.tickets.length) {
    list.innerHTML = '<div class="empty">لا توجد لديك تذاكر دعم حالياً.<br>يمكنك فتح تذكرة جديدة عند الحاجة.</div>';
    return;
  }

  list.innerHTML = state.tickets.map(ticket => `
    <article class="ticket" data-ticket="${ticket.id}">
      <div class="ticket-top">
        <span class="ticket-id">#${ticket.id}</span>
        <span class="badge ${ticket.status}">${statusText(ticket.status)}</span>
      </div>
      <h3>${escapeHtml(ticket.category)}</h3>
      <div class="ticket-meta">${escapeHtml(ticket.date)} · ${ticket.messages.length} رسالة</div>
    </article>
  `).join("");

  $$(".ticket").forEach(el => {
    el.addEventListener("click", () => openTicket(el.dataset.ticket));
  });
}

function openModal(id) {
  const modal = document.getElementById(id);
  modal.classList.add("show");
  modal.setAttribute("aria-hidden", "false");
  document.body.style.overflow = "hidden";
}

function closeModal(id) {
  const modal = document.getElementById(id);
  modal.classList.remove("show");
  modal.setAttribute("aria-hidden", "true");
  document.body.style.overflow = "";
}

function openNewTicket(category = "") {
  $("#ticketForm").reset();
  $("#category").value = category;
  openModal("ticketModal");
}

function openTicket(id) {
  const ticket = state.tickets.find(t => t.id === id);
  if (!ticket) return;

  $("#detailsId").textContent = `#${ticket.id}`;
  $("#detailsTitle").textContent = ticket.category;

  $("#conversation").innerHTML = ticket.messages.map(msg => `
    <div class="message ${msg.from}">
      ${escapeHtml(msg.text)}
      <small>${escapeHtml(msg.time)}</small>
    </div>
  `).join("");

  $("#replyForm").dataset.ticket = id;
  openModal("detailsModal");
}

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.remove("show"), 2600);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function generateTicketId() {
  const max = state.tickets.reduce((n, t) => {
    const num = Number(String(t.id).replace(/\D/g, ""));
    return Math.max(n, num || 0);
  }, 1047);
  return `CRY-${max + 1}`;
}

$$(".support-card").forEach(card => {
  card.addEventListener("click", () => openNewTicket(card.dataset.category));
});

$("#newTicketBtn").addEventListener("click", () => openNewTicket());

$$("[data-close]").forEach(btn => {
  btn.addEventListener("click", () => closeModal(btn.dataset.close));
});

$("#ticketForm").addEventListener("submit", (event) => {
  event.preventDefault();

  const file = $("#attachment").files[0];
  if (file && file.size > 5 * 1024 * 1024) {
    showToast("حجم الصورة يجب ألا يتجاوز 5MB");
    return;
  }

  const category = $("#category");
  const categoryText = category.options[category.selectedIndex]?.text || "مشكلة أخرى";
  const ticket = {
    id: generateTicketId(),
    category: categoryText.replace(/^[^\s]+\s/, ""),
    status: "open",
    date: new Date().toLocaleDateString("ar-DZ", { day: "2-digit", month: "long", year: "numeric" }),
    description: $("#description").value.trim(),
    amount: $("#amount").value.trim(),
    messages: [
      { from: "user", text: $("#description").value.trim(), time: new Date().toLocaleTimeString("ar-DZ", { hour: "2-digit", minute: "2-digit" }) }
    ]
  };

  state.tickets.unshift(ticket);
  saveState();
  renderTickets();
  closeModal("ticketModal");
  showToast(`تم إنشاء التذكرة #${ticket.id}`);
});

$("#replyForm").addEventListener("submit", (event) => {
  event.preventDefault();

  const id = event.currentTarget.dataset.ticket;
  const input = $("#replyInput");
  const text = input.value.trim();
  if (!text) return;

  const ticket = state.tickets.find(t => t.id === id);
  if (!ticket) return;

  ticket.messages.push({
    from: "user",
    text,
    time: new Date().toLocaleTimeString("ar-DZ", { hour: "2-digit", minute: "2-digit" })
  });
  ticket.status = "waiting";

  saveState();
  input.value = "";
  openTicket(id);
  renderTickets();
  showToast("تم إرسال رسالتك إلى الدعم");
});

$("#notificationsBtn").addEventListener("click", () => {
  showToast("لا توجد إشعارات جديدة");
});

$("#ticketsNav").addEventListener("click", () => {
  document.querySelector(".tickets-section").scrollIntoView({ behavior: "smooth" });
});

$("#profileNav").addEventListener("click", () => {
  showToast(`معرّف العضو: ${state.user.id}`);
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeModal("ticketModal");
    closeModal("detailsModal");
  }
});

loadState();
$("#userName").textContent = state.user.name;
renderTickets();
