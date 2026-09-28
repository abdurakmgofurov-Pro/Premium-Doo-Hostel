// Xonalar moduli: barcha sahifalar uchun umumiy dialog boshqaruvi.
//  * data-dialog="<id>" tugma dialogni ochadi; data-fill='{"nom": "qiymat"}'
//    JSON'i shu dialogdagi forma maydonlarini (name bo'yicha) to'ldiradi;
//    "_action" kaliti forma action'ini belgilaydi, data-fill-text="kalit"
//    elementlariga esa matn yoziladi.
//  * data-close-dialog — dialogni yopadi.
import "./types";

type FillMap = Record<string, string | boolean>;

function fillDialog(dialog: HTMLDialogElement, fill: FillMap): void {
  const form = dialog.querySelector<HTMLFormElement>("form");
  for (const [key, value] of Object.entries(fill)) {
    if (key === "_action") {
      if (form) form.action = String(value);
      continue;
    }
    dialog.querySelectorAll<HTMLElement>(`[data-fill-text="${key}"]`).forEach((el) => {
      el.textContent = String(value);
    });
    const field = form?.elements.namedItem(key) as HTMLInputElement | HTMLSelectElement | null;
    if (!field || field instanceof RadioNodeList) continue;
    if (field instanceof HTMLInputElement && field.type === "checkbox") {
      field.checked = Boolean(value);
    } else {
      const text = String(value);
      // 0 narx maydonda "0.0" emas, bo'sh ko'rinsin
      field.value = key === "price" && Number(text) === 0 ? "" : text;
    }
  }
  const booking = dialog.querySelector<HTMLSelectElement>("#checkinBooking");
  if (booking && "booking_id" in fill) booking.dispatchEvent(new Event("change"));
}

document.querySelectorAll<HTMLElement>("[data-dialog]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const dialog = document.getElementById(btn.getAttribute("data-dialog") || "") as HTMLDialogElement | null;
    if (!dialog) return;
    dialog.querySelector<HTMLFormElement>("form")?.reset();
    const raw = btn.getAttribute("data-fill");
    if (raw) fillDialog(dialog, JSON.parse(raw) as FillMap);
    dialog.showModal();
  });
});

document.querySelectorAll<HTMLElement>("[data-close-dialog]").forEach((btn) => {
  btn.addEventListener("click", () => btn.closest("dialog")?.close());
});

// Bron tanlansa — mehmon ismi va rejalashtirilgan ketish sanasi avtomatik to'ldiriladi.
const bookingSelect = document.getElementById("checkinBooking") as HTMLSelectElement | null;
if (bookingSelect) {
  bookingSelect.addEventListener("change", () => {
    const opt = bookingSelect.selectedOptions[0];
    const form = bookingSelect.closest("form") as HTMLFormElement;
    if (!opt || !opt.value) return;
    (form.elements.namedItem("guest_name") as HTMLInputElement).value = opt.dataset.guest || "";
    (form.elements.namedItem("expected_departure") as HTMLInputElement).value = opt.dataset.departure || "";
  });
}

// Xona qo'shishda tur tanlansa — sig'im va narx turdan olinadi (keyin o'zgartirish mumkin).
const typeSelect = document.getElementById("roomTypeSelect") as HTMLSelectElement | null;
if (typeSelect) {
  typeSelect.addEventListener("change", () => {
    const opt = typeSelect.selectedOptions[0];
    const form = typeSelect.closest("form") as HTMLFormElement;
    if (!opt || !opt.value) return;
    (form.elements.namedItem("capacity") as HTMLInputElement).value = opt.dataset.capacity || "";
    const price = Number(opt.dataset.price || 0);
    (form.elements.namedItem("price") as HTMLInputElement).value = price ? String(price) : "";
    (form.elements.namedItem("currency") as HTMLSelectElement).value = opt.dataset.currency || "UZS";
  });
}
