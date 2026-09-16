"use strict";
(() => {
  // src/cash.ts
  (function editModal() {
    const modal = document.getElementById("cashEditModal");
    if (!modal) return;
    const form = document.getElementById("cashEditForm");
    document.querySelectorAll(".cash-edit-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        form.action = "/cash/" + btn.getAttribute("data-id") + "/edit";
        document.getElementById("editDate").value = btn.getAttribute("data-date") || "";
        document.getElementById("editSource").value = btn.getAttribute("data-source") || "";
        document.getElementById("editAmount").value = btn.getAttribute("data-amount") || "";
        document.getElementById("editCurrency").value = btn.getAttribute("data-currency") || "";
        document.getElementById("editCounterparty").value = btn.getAttribute("data-counterparty") || "";
        document.getElementById("editNoteLabel").value = btn.getAttribute("data-note-label") || "";
        document.getElementById("editDescription").value = btn.getAttribute("data-description") || "";
        modal.showModal();
      });
    });
    document.getElementById("closeCashEditBtn").addEventListener("click", () => modal.close());
  })();
  (function addModal() {
    const modal = document.getElementById("cashAddModal");
    const openBtn = document.getElementById("openCashAddBtn");
    if (!modal || !openBtn) return;
    openBtn.addEventListener("click", () => modal.showModal());
    document.getElementById("closeCashAddBtn").addEventListener("click", () => modal.close());
  })();
  (function categoryToggle() {
    const typeSelect = document.getElementById("cashTypeSelect");
    if (!typeSelect) return;
    const incomeField = document.getElementById("incomeCatField");
    const expenseField = document.getElementById("expenseCatField");
    const incomeSelect = document.getElementById("incomeCatSelect");
    const expenseSelect = document.getElementById("expenseCatSelect");
    const forma2Field = document.getElementById("forma2Field");
    const forma2Select = document.getElementById("forma2Select");
    function sync() {
      const isExpense = typeSelect.value === "expense";
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
})();
