"use strict";
(() => {
  // src/bookings.ts
  document.getElementById("searchBox").addEventListener("input", function() {
    const q = this.value.toLowerCase();
    document.querySelectorAll("#bookingsTable tbody tr").forEach((tr) => {
      tr.style.display = (tr.textContent || "").toLowerCase().includes(q) ? "" : "none";
    });
  });
})();
