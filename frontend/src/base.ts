// Ported 1:1 from templates/base.html's inline <script> (money-input digit
// grouping, delete-confirmation dialogs, CSRF token auto-injection). Loaded
// on every page via base.html, before any page-specific bundle.
import "./types";

function groupDigits(raw: string): string {
  const parts = raw.split(".");
  let intPart = parts[0].replace(/\s/g, "");
  const decPart = parts.length > 1 ? parts.slice(1).join("") : null;
  intPart = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  return decPart !== null ? intPart + "." + decPart : intPart;
}

// Summa kiritish maydonlari (.money-input): yozayotganda mingliklarni
// bo'sh joy bilan ajratib ko'rsatadi (masalan "51202" -> "51 202"),
// yuborishdan oldin esa bo'sh joylarni olib tashlaydi (server oddiy son kutadi).
document.addEventListener("input", (e: Event) => {
  const el = e.target as HTMLInputElement;
  if (!el.matches || !el.matches(".money-input")) return;
  const cursorFromEnd = el.value.length - (el.selectionStart ?? el.value.length);
  let raw = el.value.replace(/[^\d.]/g, "");
  const firstDot = raw.indexOf(".");
  if (firstDot !== -1) {
    raw = raw.slice(0, firstDot + 1) + raw.slice(firstDot + 1).replace(/\./g, "");
  }
  const newVal = groupDigits(raw);
  el.value = newVal;
  const pos = Math.max(0, newVal.length - cursorFromEnd);
  el.setSelectionRange(pos, pos);
});

document.addEventListener("submit", (e: Event) => {
  const form = e.target as HTMLFormElement;
  const fields = form.querySelectorAll ? form.querySelectorAll<HTMLInputElement>(".money-input") : [];
  fields.forEach((el) => { el.value = el.value.replace(/\s/g, ""); });
});

// Forma o'chirish tasdiqlash: matn data-confirm atributi orqali o'qiladi,
// eski inline onsubmit-ichidagi JS satr sifatida emas — chunki tarjima
// matnida apostrof (') bo'lsa, JS satr sinib, tasdiqlash oynasi
// umuman chiqmasdi.
document.addEventListener("submit", (e: Event) => {
  const form = e.target as HTMLFormElement;
  const msg = form.getAttribute && form.getAttribute("data-confirm");
  if (msg && !window.confirm(msg)) e.preventDefault();
});

// CSRF himoyasi: har bir POST formaga (agar hali qo'shilmagan bo'lsa)
// yuborilishdan oldin sessiya tokeni avtomatik qo'shiladi — shablonlarni
// birma-bir tahrirlash o'rniga shu yerda markazlashtirilgan.
document.addEventListener("submit", (e: Event) => {
  const form = e.target as HTMLFormElement;
  if (!form.method || form.method.toLowerCase() !== "post") return;
  if (form.querySelector('input[name="csrf_token"]')) return;
  const inp = document.createElement("input");
  inp.type = "hidden";
  inp.name = "csrf_token";
  inp.value = window.CSRF_TOKEN || "";
  form.appendChild(inp);
});
