// Shaxmatka (Exely'dagidek):
//  * bron chizig'i ustiga borganda — qisqa kartochka (turish, mehmon, manba, summa/to'langan/balans);
//  * bron chizig'ini bosganda — o'ng tomondan tafsilot paneli (serverdan yuklanadi);
//  * «joy tayinlanmagan» raqamini bosganda — o'sha kunning taqsimlanmagan bronlari ro'yxati.
// Ma'lumot data-tip / data-un atributlarida; barcha matn textContent orqali qo'yiladi (XSS xavfsiz).
import "./types";

type Status = "new" | "in" | "out";

interface TipInfo {
  id: number;
  guest: string;
  arrival: string;
  departure: string;
  arrival_at: string;
  departure_at: string;
  nights: number;
  bed: string;
  status: Status;
  channel: string;
  comment: string;
  ref: string;
  total: number | null;
  paid: number | null;
  balance: number | null;
  currency: string;
}

interface UnEntry {
  id: number;
  ref: string;
  guest: string;
  arrival_at: string;
  departure_at: string;
  paid: number | null;
  balance: number | null;
  currency: string;
}

interface Detail {
  id: number;
  ref: string;
  bed: string;
  guest: string;
  customer: string;
  phone: string;
  status: Status;
  type: string;
  arrival_at: string;
  departure_at: string;
  actual_in_at: string;
  actual_out_at: string;
  nights: number | null;
  booked_at: string;
  rate_plan: string;
  adults: number | null;
  children: number | null;
  services: string[];
  source: string;
  guarantee: string;
  comment: string;
  total: number | null;
  paid: number | null;
  balance: number | null;
  currency: string;
}

const T = (key: string): string => window.T[key] || key;
const sourceLabel = (s: string): string => (s === "At front desk" ? T("rooms.src_front_desk") : s);
const STATUS_KEY: Record<Status, string> = { new: "rooms.lg_new", in: "rooms.lg_in", out: "rooms.lg_out" };

const money = (v: number | null, cur: string): string =>
  v === null || v === undefined ? "—" : `${v.toLocaleString("ru-RU", { maximumFractionDigits: 2 })} ${cur}`.trim();
const dt = (s: string): string => (s ? s.replace("T", " ").slice(0, 16) : "—");

function el(tag: string, value = "", cls = ""): HTMLElement {
  const e = document.createElement(tag);
  if (value) e.textContent = value;
  if (cls) e.className = cls;
  return e;
}

function statusBadge(status: Status): HTMLElement {
  const s = el("span");
  s.append(el("i", "", `dot ${status}`), document.createTextNode(T(STATUS_KEY[status])));
  return s;
}

function row(label: string, value: string | HTMLElement, cls = "tr"): HTMLElement {
  const r = el("div", "", cls);
  r.append(el("span", label));
  const v = el("span");
  if (typeof value === "string") v.textContent = value;
  else v.append(value);
  r.append(v);
  return r;
}

/* ------------------------------------------------------------ hover kartochkasi */

const tip = el("div", "", "cc-tip");
tip.hidden = true;
document.body.appendChild(tip);

function showTip(bar: HTMLElement): void {
  const i = JSON.parse(bar.dataset.tip || "{}") as TipInfo;
  const type = bar.closest<HTMLElement>(".cc-bed")?.dataset.type || "";
  tip.replaceChildren(el("div", i.guest, "tt"));
  tip.append(row(T("rooms.tip_stay"), `${dt(i.arrival_at)} → ${dt(i.departure_at)}`));
  tip.append(row(T("rooms.tip_nights"), String(i.nights)), row(T("rooms.tip_bed"), i.bed));
  if (type) tip.append(row(T("rooms.tip_type"), type));
  tip.append(row(T("rooms.tip_status"), statusBadge(i.status)));
  tip.append(row(T("rooms.tip_channel"), `${sourceLabel(i.channel) || "—"}${i.ref ? ` (${i.ref})` : ""}`));
  if (i.comment) tip.append(row(T("rooms.tip_comment"), i.comment));
  if (i.total !== null) {
    tip.append(
      row(T("rooms.tip_total"), money(i.total, i.currency)),
      row(T("rooms.tip_paid"), money(i.paid, i.currency)),
      row(T("rooms.tip_balance"), money(i.balance, i.currency)),
    );
  }
}

function showUnassignedTip(cell: HTMLElement): void {
  const list = JSON.parse(cell.dataset.un || "[]") as UnEntry[];
  tip.replaceChildren(el("div", T("rooms.chart_unassigned"), "tt"));
  list.forEach((u) => tip.append(el("div", `${u.guest} · ${dt(u.arrival_at)} → ${dt(u.departure_at)}`, "li")));
  tip.append(el("div", T("rooms.un_click"), "li hint"));
}

function placeTip(ev: MouseEvent): void {
  const pad = 14;
  let x = ev.clientX + pad;
  let y = ev.clientY + pad;
  const r = tip.getBoundingClientRect();
  if (x + r.width > window.innerWidth - 8) x = ev.clientX - r.width - pad;
  if (y + r.height > window.innerHeight - 8) y = ev.clientY - r.height - pad;
  tip.style.left = `${Math.max(x, 8)}px`;
  tip.style.top = `${Math.max(y, 8)}px`;
}

/* ------------------------------------------------------------ o'ng panel */

const drawer = document.getElementById("ccDrawer") as HTMLElement | null;
const drawerTitle = document.getElementById("ccDrawerTitle") as HTMLElement | null;
const drawerBody = document.getElementById("ccDrawerBody") as HTMLElement | null;

function closeDrawer(): void {
  if (drawer) drawer.hidden = true;
}

async function openDrawer(id: number, fallbackTitle: string): Promise<void> {
  if (!drawer || !drawerTitle || !drawerBody) return;
  drawerTitle.textContent = fallbackTitle;
  drawerBody.replaceChildren(el("div", T("rooms.dr_loading"), "dr-msg"));
  drawer.hidden = false;
  try {
    const resp = await fetch(`/rooms/chart/booking/${id}`, { headers: { Accept: "application/json" } });
    if (!resp.ok) throw new Error(String(resp.status));
    renderDetail((await resp.json()) as Detail);
  } catch {
    drawerBody.replaceChildren(el("div", T("rooms.dr_error"), "dr-msg"));
  }
}

function renderDetail(d: Detail): void {
  if (!drawerTitle || !drawerBody) return;
  drawerTitle.textContent = `${d.bed} | ${d.guest}`;
  const sections: HTMLElement[][] = [];
  const add = (section: HTMLElement[], label: string, value: string | HTMLElement | null | undefined): void => {
    if (value === null || value === undefined || value === "") return;
    section.push(row(label, value, "tr dr"));
  };
  const s1: HTMLElement[] = [];
  add(s1, T("rooms.tip_status"), statusBadge(d.status));
  add(s1, T("rooms.tip_ref"), d.ref);
  add(s1, T("rooms.dr_customer"), d.customer);
  add(s1, T("rooms.dr_phone"), d.phone);
  const s2: HTMLElement[] = [];
  add(s2, T("rooms.dr_checkin"), dt(d.actual_in_at || d.arrival_at));
  add(s2, T("rooms.dr_checkout"), dt(d.actual_out_at || d.departure_at));
  add(s2, T("rooms.dr_booked"), d.booked_at);
  add(s2, T("rooms.tip_nights"), d.nights === null ? "" : String(d.nights));
  add(s2, T("rooms.dr_rate"), d.rate_plan);
  add(s2, T("rooms.tip_type"), d.type);
  const s3: HTMLElement[] = [];
  add(s3, T("rooms.dr_adults"), d.adults === null ? "" : `${d.adults ?? 0} | ${d.children ?? 0}`);
  add(s3, T("rooms.dr_guest"), d.guest);
  const s4: HTMLElement[] = [];
  add(s4, T("rooms.dr_services"), d.services.join(", "));
  add(s4, T("rooms.dr_source"), d.source);
  add(s4, T("rooms.dr_guarantee"), d.guarantee);
  add(s4, T("rooms.tip_comment"), d.comment);
  const s5: HTMLElement[] = [];
  if (d.total !== null) {
    add(s5, T("rooms.dr_total"), money(d.total, d.currency));
    add(s5, T("rooms.dr_paid"), money(d.paid, d.currency));
    add(s5, T("rooms.dr_balance"), money(d.balance, d.currency));
  }
  sections.push(s1, s2, s3, s4, s5);
  const nodes: HTMLElement[] = [];
  sections.filter((s) => s.length).forEach((s, idx) => {
    if (idx > 0) nodes.push(el("hr"));
    nodes.push(...s);
  });
  drawerBody.replaceChildren(...nodes);
}

/* ------------------------------------------------------------ taqsimlanmagan bronlar oynasi */

const unDialog = document.getElementById("unDialog") as HTMLDialogElement | null;
const unTitle = document.getElementById("unTitle") as HTMLElement | null;
const unBody = document.getElementById("unBody") as HTMLElement | null;

function openUnassigned(cell: HTMLElement): void {
  if (!unDialog || !unTitle || !unBody) return;
  const list = JSON.parse(cell.dataset.un || "[]") as UnEntry[];
  unTitle.textContent = T("rooms.un_title").replace("{date}", cell.dataset.date || "");
  unBody.replaceChildren(
    ...list.map((u) => {
      const tr = document.createElement("tr");
      const open = el("button", "≡", "btn small");
      (open as HTMLButtonElement).type = "button";
      open.addEventListener("click", () => {
        unDialog.close();
        void openDrawer(u.id, u.guest);
      });
      const cells = [
        el("td", u.ref || "—", "mono"),
        el("td", u.guest),
        el("td", dt(u.arrival_at)),
        el("td", dt(u.departure_at)),
        el("td", money(u.paid, u.currency)),
        el("td", money(u.balance, u.currency)),
      ];
      const last = document.createElement("td");
      last.append(open);
      tr.append(...cells, last);
      return tr;
    }),
  );
  unDialog.showModal();
}

/* ------------------------------------------------------------ hodisalar */

const scroll = document.querySelector<HTMLElement>(".cc-scroll");
if (scroll) {
  scroll.addEventListener("mouseover", (ev) => {
    const target = ev.target as HTMLElement;
    const bar = target.closest<HTMLElement>(".cc-bar");
    const un = target.closest<HTMLElement>(".un");
    if (bar && bar.dataset.tip) showTip(bar);
    else if (un && un.dataset.un) showUnassignedTip(un);
    else return;
    tip.hidden = false;
    placeTip(ev);
  });
  scroll.addEventListener("mousemove", (ev) => {
    if (!tip.hidden) placeTip(ev);
  });
  scroll.addEventListener("mouseout", (ev) => {
    const to = (ev as MouseEvent).relatedTarget as HTMLElement | null;
    if (!to || !(to.closest(".cc-bar") || to.closest(".un"))) tip.hidden = true;
  });
  scroll.addEventListener("scroll", () => {
    tip.hidden = true;
  });
  scroll.addEventListener("click", (ev) => {
    const target = ev.target as HTMLElement;
    const bar = target.closest<HTMLElement>(".cc-bar");
    const un = target.closest<HTMLElement>(".un");
    tip.hidden = true;
    if (bar && bar.dataset.tip) {
      const i = JSON.parse(bar.dataset.tip) as TipInfo;
      void openDrawer(i.id, `${i.bed} | ${i.guest}`);
    } else if (un && un.dataset.un) {
      openUnassigned(un);
    }
  });
}

document.getElementById("ccDrawerClose")?.addEventListener("click", closeDrawer);
document.addEventListener("keydown", (ev) => {
  if (ev.key === "Escape") closeDrawer();
});
document.addEventListener("click", (ev) => {
  if (!drawer || drawer.hidden) return;
  const target = ev.target as HTMLElement;
  if (!target.closest("#ccDrawer") && !target.closest(".cc-bar") && !target.closest("#unDialog")) closeDrawer();
});
document.querySelectorAll<HTMLElement>("[data-close-dialog]").forEach((b) =>
  b.addEventListener("click", () => b.closest("dialog")?.close()),
);
