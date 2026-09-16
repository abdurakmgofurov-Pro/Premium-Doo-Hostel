"use strict";
(() => {
  // src/counterparties.ts
  (function() {
    const modal = document.getElementById("cpEditModal");
    if (!modal) return;
    const form = document.getElementById("cpEditForm");
    document.querySelectorAll(".cp-edit-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        form.action = "/ledger/counterparties/" + btn.getAttribute("data-id") + "/edit";
        document.getElementById("editCpName").value = btn.getAttribute("data-name") || "";
        document.getElementById("editCpInn").value = btn.getAttribute("data-inn") || "";
        modal.showModal();
      });
    });
    document.getElementById("closeCpEditBtn").addEventListener("click", () => modal.close());
  })();
})();
