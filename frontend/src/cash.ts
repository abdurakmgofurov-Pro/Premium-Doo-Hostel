// Ported 1:1 from templates/cash.html's inline <script> blocks: the
// edit modal, the add modal, and the income/expense category-field toggle
// (including the Forma 2 bridge category select).
import "./types";

(function editModal() {
  const modal = document.getElementById("cashEditModal") as HTMLDialogElement | null;
  if (!modal) return;
  const form = document.getElementById("cashEditForm") as HTMLFormElement;
  document.querySelectorAll<HTMLButtonElement>(".cash-edit-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      form.action = "/cash/" + btn.getAttribute("data-id") + "/edit";
      (document.getElementById("editDate") as HTMLInputElement).value = btn.getAttribute("data-date") || "";
      (document.getElementById("editSource") as HTMLSelectElement).value = btn.getAttribute("data-source") || "";
      (document.getElementById("editAmount") as HTMLInputElement).value = btn.getAttribute("data-amount") || "";
      (document.getElementById("editCurrency") as HTMLSelectElement).value = btn.getAttribute("data-currency") || "";
      (document.getElementById("editCounterparty") as HTMLInputElement).value = btn.getAttribute("data-counterparty") || "";
      (document.getElementById("editNoteLabel") as HTMLInputElement).value = btn.getAttribute("data-note-label") || "";
      (document.getElementById("editDescription") as HTMLInputElement).value = btn.getAttribute("data-description") || "";
      modal.showModal();
    });
  });
  document.getElementById("closeCashEditBtn")!.addEventListener("click", () => modal.close());
})();

(function addModal() {
  const modal = document.getElementById("cashAddModal") as HTMLDialogElement | null;
  const openBtn = document.getElementById("openCashAddBtn") as HTMLButtonElement | null;
  if (!modal || !openBtn) return;
  openBtn.addEventListener("click", () => modal.showModal());
  document.getElementById("closeCashAddBtn")!.addEventListener("click", () => modal.close());
})();

(function categoryToggle() {
  const typeSelect = document.getElementById("cashTypeSelect") as HTMLSelectElement | null;
  if (!typeSelect) return;
  const incomeField = document.getElementById("incomeCatField") as HTMLElement;
  const expenseField = document.getElementById("expenseCatField") as HTMLElement;
  const incomeSelect = document.getElementById("incomeCatSelect") as HTMLSelectElement;
  const expenseSelect = document.getElementById("expenseCatSelect") as HTMLSelectElement;
  const forma2Field = document.getElementById("forma2Field") as HTMLElement;
  const forma2Select = document.getElementById("forma2Select") as HTMLSelectElement;

  function sync(): void {
    const isExpense = typeSelect!.value === "expense";
    incomeField.style.display = isExpense ? "none" : "";
    incomeSelect.disabled = isExpense;
    expenseField.style.display = isExpense ? "" : "none";
    expenseSelect.disabled = !isExpense;
    forma2Field.style.display = isExpense ? "" : "none";
    forma2Select.disabled = !isExpense;
    if (!isExpense) forma2Select.value = "";
  }

  typeSelect.addEventListener("change", sync);
  sync();
})();
