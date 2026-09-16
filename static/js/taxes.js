"use strict";
(() => {
  // src/taxes.ts
  (function() {
    const modal = document.getElementById("taxModal");
    if (!modal) return;
    const title = document.getElementById("taxModalTitle");
    document.querySelectorAll(".tax-edit").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.getElementById("taxNameInput").value = btn.getAttribute("data-name") || "";
        document.getElementById("taxAccruedInput").value = btn.getAttribute("data-accrued") || "";
        document.getElementById("taxPaidInput").value = btn.getAttribute("data-paid") || "";
        title.textContent = btn.getAttribute("data-name");
        modal.showModal();
      });
    });
    document.getElementById("closeTaxModalBtn").addEventListener("click", () => modal.close());
  })();
})();
