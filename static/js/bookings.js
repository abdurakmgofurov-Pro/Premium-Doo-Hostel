"use strict";
(() => {
  // src/bookings.ts
  document.getElementById("searchBox").addEventListener("input", function() {
    const q = this.value.toLowerCase();
    document.querySelectorAll("#bookingsTable tbody tr.booking-row").forEach((tr) => {
      const match = (tr.textContent || "").toLowerCase().includes(q);
      tr.style.display = match ? "" : "none";
      const detail = tr.nextElementSibling;
      if (detail && detail.classList.contains("booking-detail") && !match) {
        detail.hidden = true;
        const btn = tr.querySelector(".booking-expand");
        if (btn) {
          btn.setAttribute("aria-expanded", "false");
          btn.textContent = "\u25B8";
        }
      }
    });
  });
  document.querySelectorAll(".booking-expand").forEach((btn) => {
    btn.addEventListener("click", () => {
      const row = btn.closest("tr");
      const detail = row?.nextElementSibling;
      if (!detail || !detail.classList.contains("booking-detail")) return;
      const open = detail.hidden;
      detail.hidden = !open;
      btn.setAttribute("aria-expanded", String(open));
      btn.textContent = open ? "\u25BE" : "\u25B8";
    });
  });
})();
