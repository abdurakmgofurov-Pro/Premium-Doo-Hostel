"use strict";
(() => {
  // src/transactions.ts
  (function() {
    const typeSelect = document.getElementById("txType");
    if (!typeSelect) return;
    const expenseField = document.getElementById("expenseCategoryField");
    const incomeField = document.getElementById("incomeCategoryField");
    const expenseSelect = document.getElementById("expenseCategorySelect");
    const incomeSelect = document.getElementById("incomeCategorySelect");
    function sync() {
      const isIncome = typeSelect.value === "income";
      expenseField.style.display = isIncome ? "none" : "";
      incomeField.style.display = isIncome ? "" : "none";
      expenseSelect.disabled = isIncome;
      incomeSelect.disabled = !isIncome;
    }
    typeSelect.addEventListener("change", sync);
    sync();
  })();
})();
