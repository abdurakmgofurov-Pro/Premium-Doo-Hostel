"use strict";
(() => {
  // src/rooms.ts
  function fillDialog(dialog, fill) {
    const form = dialog.querySelector("form");
    for (const [key, value] of Object.entries(fill)) {
      if (key === "_action") {
        if (form) form.action = String(value);
        continue;
      }
      dialog.querySelectorAll(`[data-fill-text="${key}"]`).forEach((el) => {
        el.textContent = String(value);
      });
      const field = form?.elements.namedItem(key);
      if (!field || field instanceof RadioNodeList) continue;
      if (field instanceof HTMLInputElement && field.type === "checkbox") {
        field.checked = Boolean(value);
      } else {
        const text = String(value);
        field.value = key === "price" && Number(text) === 0 ? "" : text;
      }
    }
    const booking = dialog.querySelector("#checkinBooking");
    if (booking && "booking_id" in fill) booking.dispatchEvent(new Event("change"));
  }
  document.querySelectorAll("[data-dialog]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const dialog = document.getElementById(btn.getAttribute("data-dialog") || "");
      if (!dialog) return;
      dialog.querySelector("form")?.reset();
      const raw = btn.getAttribute("data-fill");
      if (raw) fillDialog(dialog, JSON.parse(raw));
      dialog.showModal();
    });
  });
  document.querySelectorAll("[data-close-dialog]").forEach((btn) => {
    btn.addEventListener("click", () => btn.closest("dialog")?.close());
  });
  var bookingSelect = document.getElementById("checkinBooking");
  if (bookingSelect) {
    bookingSelect.addEventListener("change", () => {
      const opt = bookingSelect.selectedOptions[0];
      const form = bookingSelect.closest("form");
      if (!opt || !opt.value) return;
      form.elements.namedItem("guest_name").value = opt.dataset.guest || "";
      form.elements.namedItem("expected_departure").value = opt.dataset.departure || "";
    });
  }
  var typeSelect = document.getElementById("roomTypeSelect");
  if (typeSelect) {
    typeSelect.addEventListener("change", () => {
      const opt = typeSelect.selectedOptions[0];
      const form = typeSelect.closest("form");
      if (!opt || !opt.value) return;
      form.elements.namedItem("capacity").value = opt.dataset.capacity || "";
      const price = Number(opt.dataset.price || 0);
      form.elements.namedItem("price").value = price ? String(price) : "";
      form.elements.namedItem("currency").value = opt.dataset.currency || "UZS";
    });
  }
})();
