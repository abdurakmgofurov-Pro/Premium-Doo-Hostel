// Ported 1:1 from templates/services.html's three inline <script> blocks:
// the edit modal (with VAT recalculation), the add modal, and the add
// form's own VAT recalculation.
import "./types";

declare global {
  interface Window {
    VAT_RATE: number;
  }
}

(function editModal() {
  const modal = document.getElementById("serviceEditModal") as HTMLDialogElement | null;
  if (!modal) return;
  const form = document.getElementById("serviceEditForm") as HTMLFormElement;
  const noVat = document.getElementById("editSvcAmountNoVat") as HTMLInputElement;
  const vatDisplay = document.getElementById("editSvcVatDisplay") as HTMLInputElement;
  const totalDisplay = document.getElementById("editSvcTotalDisplay") as HTMLInputElement;
  function recalcEdit(): void {
    const raw = noVat.value.replace(/\s/g, "");
    const n = parseFloat(raw) || 0;
    const vat = Math.round(n * window.VAT_RATE * 100) / 100;
    vatDisplay.value = vat.toLocaleString("ru-RU");
    totalDisplay.value = (n + vat).toLocaleString("ru-RU");
  }
  noVat.addEventListener("input", recalcEdit);
  document.querySelectorAll<HTMLButtonElement>(".service-edit-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      form.action = "/services/" + btn.getAttribute("data-id") + "/edit";
      (document.getElementById("editSvcDate") as HTMLInputElement).value = btn.getAttribute("data-date") || "";
      (document.getElementById("editSvcCounterparty") as HTMLInputElement).value = btn.getAttribute("data-counterparty") || "";
      (document.getElementById("editSvcServiceType") as HTMLInputElement).value = btn.getAttribute("data-service-type") || "";
      noVat.value = btn.getAttribute("data-amount-no-vat") || "";
      (document.getElementById("editSvcCurrency") as HTMLSelectElement).value = btn.getAttribute("data-currency") || "";
      (document.getElementById("editSvcStatus") as HTMLSelectElement).value = btn.getAttribute("data-status") || "";
      (document.getElementById("editSvcDescription") as HTMLInputElement).value = btn.getAttribute("data-description") || "";
      recalcEdit();
      modal.showModal();
    });
  });
  document.getElementById("closeServiceEditBtn")!.addEventListener("click", () => modal.close());
})();

(function addModal() {
  const modal = document.getElementById("serviceAddModal") as HTMLDialogElement | null;
  const openBtn = document.getElementById("openServiceAddBtn") as HTMLButtonElement | null;
  if (!modal || !openBtn) return;
  openBtn.addEventListener("click", () => modal.showModal());
  document.getElementById("closeServiceAddBtn")!.addEventListener("click", () => modal.close());
})();

(function addFormVat() {
  const noVatInput = document.getElementById("svcAmountNoVat") as HTMLInputElement | null;
  const vatDisplay = document.getElementById("svcVatDisplay") as HTMLInputElement;
  const totalDisplay = document.getElementById("svcTotalDisplay") as HTMLInputElement;
  if (!noVatInput) return;
  function recalc(): void {
    const raw = noVatInput!.value.replace(/\s/g, "").replace(/ /g, "");
    const n = parseFloat(raw) || 0;
    const vat = Math.round(n * window.VAT_RATE * 100) / 100;
    vatDisplay.value = vat.toLocaleString("ru-RU");
    totalDisplay.value = (n + vat).toLocaleString("ru-RU");
  }
  noVatInput.addEventListener("input", recalc);
  recalc();
})();
