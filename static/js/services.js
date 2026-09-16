"use strict";
(() => {
  // src/services.ts
  (function editModal() {
    const modal = document.getElementById("serviceEditModal");
    if (!modal) return;
    const form = document.getElementById("serviceEditForm");
    const noVat = document.getElementById("editSvcAmountNoVat");
    const vatDisplay = document.getElementById("editSvcVatDisplay");
    const totalDisplay = document.getElementById("editSvcTotalDisplay");
    function recalcEdit() {
      const raw = noVat.value.replace(/\s/g, "");
      const n = parseFloat(raw) || 0;
      const vat = Math.round(n * window.VAT_RATE * 100) / 100;
      vatDisplay.value = vat.toLocaleString("ru-RU");
      totalDisplay.value = (n + vat).toLocaleString("ru-RU");
    }
    noVat.addEventListener("input", recalcEdit);
    document.querySelectorAll(".service-edit-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        form.action = "/services/" + btn.getAttribute("data-id") + "/edit";
        document.getElementById("editSvcDate").value = btn.getAttribute("data-date") || "";
        document.getElementById("editSvcCounterparty").value = btn.getAttribute("data-counterparty") || "";
        document.getElementById("editSvcServiceType").value = btn.getAttribute("data-service-type") || "";
        noVat.value = btn.getAttribute("data-amount-no-vat") || "";
        document.getElementById("editSvcCurrency").value = btn.getAttribute("data-currency") || "";
        document.getElementById("editSvcStatus").value = btn.getAttribute("data-status") || "";
        document.getElementById("editSvcDescription").value = btn.getAttribute("data-description") || "";
        recalcEdit();
        modal.showModal();
      });
    });
    document.getElementById("closeServiceEditBtn").addEventListener("click", () => modal.close());
  })();
  (function addModal() {
    const modal = document.getElementById("serviceAddModal");
    const openBtn = document.getElementById("openServiceAddBtn");
    if (!modal || !openBtn) return;
    openBtn.addEventListener("click", () => modal.showModal());
    document.getElementById("closeServiceAddBtn").addEventListener("click", () => modal.close());
  })();
  (function addFormVat() {
    const noVatInput = document.getElementById("svcAmountNoVat");
    const vatDisplay = document.getElementById("svcVatDisplay");
    const totalDisplay = document.getElementById("svcTotalDisplay");
    if (!noVatInput) return;
    function recalc() {
      const raw = noVatInput.value.replace(/\s/g, "").replace(/ /g, "");
      const n = parseFloat(raw) || 0;
      const vat = Math.round(n * window.VAT_RATE * 100) / 100;
      vatDisplay.value = vat.toLocaleString("ru-RU");
      totalDisplay.value = (n + vat).toLocaleString("ru-RU");
    }
    noVatInput.addEventListener("input", recalc);
    recalc();
  })();
})();
