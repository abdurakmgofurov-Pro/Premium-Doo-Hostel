// Ported 1:1 from templates/taxes.html's inline <script>: the accrued/paid
// edit modal.
import "./types";

(function () {
  const modal = document.getElementById("taxModal") as HTMLDialogElement | null;
  if (!modal) return;
  const title = document.getElementById("taxModalTitle") as HTMLElement;
  document.querySelectorAll<HTMLButtonElement>(".tax-edit").forEach((btn) => {
    btn.addEventListener("click", () => {
      (document.getElementById("taxNameInput") as HTMLInputElement).value = btn.getAttribute("data-name") || "";
      (document.getElementById("taxAccruedInput") as HTMLInputElement).value = btn.getAttribute("data-accrued") || "";
      (document.getElementById("taxPaidInput") as HTMLInputElement).value = btn.getAttribute("data-paid") || "";
      title.textContent = btn.getAttribute("data-name");
      modal.showModal();
    });
  });
  document.getElementById("closeTaxModalBtn")!.addEventListener("click", () => modal.close());
})();
