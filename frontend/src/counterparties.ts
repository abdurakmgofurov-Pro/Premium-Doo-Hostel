// Ported 1:1 from templates/counterparties.html's inline <script>: the
// name/INN edit modal.
import "./types";

(function () {
  const modal = document.getElementById("cpEditModal") as HTMLDialogElement | null;
  if (!modal) return;
  const form = document.getElementById("cpEditForm") as HTMLFormElement;
  document.querySelectorAll<HTMLButtonElement>(".cp-edit-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      form.action = "/ledger/counterparties/" + btn.getAttribute("data-id") + "/edit";
      (document.getElementById("editCpName") as HTMLInputElement).value = btn.getAttribute("data-name") || "";
      (document.getElementById("editCpInn") as HTMLInputElement).value = btn.getAttribute("data-inn") || "";
      modal.showModal();
    });
  });
  document.getElementById("closeCpEditBtn")!.addEventListener("click", () => modal.close());
})();
