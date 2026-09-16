// Ported 1:1 from templates/transactions.html's inline <script>: toggles
// between the expense-category and income-category selects based on the
// chosen transaction type.
import "./types";

(function () {
  const typeSelect = document.getElementById("txType") as HTMLSelectElement | null;
  if (!typeSelect) return;
  const expenseField = document.getElementById("expenseCategoryField") as HTMLElement;
  const incomeField = document.getElementById("incomeCategoryField") as HTMLElement;
  const expenseSelect = document.getElementById("expenseCategorySelect") as HTMLSelectElement;
  const incomeSelect = document.getElementById("incomeCategorySelect") as HTMLSelectElement;

  function sync(): void {
    const isIncome = typeSelect!.value === "income";
    expenseField.style.display = isIncome ? "none" : "";
    incomeField.style.display = isIncome ? "" : "none";
    expenseSelect.disabled = isIncome;
    incomeSelect.disabled = !isIncome;
  }

  typeSelect.addEventListener("change", sync);
  sync();
})();
