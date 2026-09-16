"use strict";
(() => {
  // src/sklad.ts
  (function marginCalc() {
    function raw(el) {
      if (!el) return NaN;
      const v = (el.value || "").replace(/\s/g, "");
      return v === "" ? NaN : parseFloat(v);
    }
    function fmtMoney(n) {
      if (!isFinite(n)) return "";
      const parts = n.toFixed(2).split(".");
      parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, " ");
      return parts.join(".");
    }
    function fmtPct(n) {
      if (!isFinite(n)) return "";
      return (Math.round(n * 100) / 100).toString();
    }
    document.addEventListener("input", (e) => {
      const el = e.target;
      const form = el.closest ? el.closest("form") : null;
      if (!form) return;
      const cost = form.querySelector("[name=cost_price]");
      const sale = form.querySelector("[name=sale_price]");
      const pct = form.querySelector(".margin-pct-input");
      if (!cost || !sale || !pct) return;
      const c = raw(cost);
      if (el === pct) {
        const p = raw(pct);
        if (isFinite(c) && c > 0 && isFinite(p)) sale.value = fmtMoney(c * (1 + p / 100));
      } else if (el === cost) {
        const p2 = raw(pct);
        if (isFinite(c) && c > 0 && isFinite(p2)) sale.value = fmtMoney(c * (1 + p2 / 100));
      } else if (el === sale) {
        const s = raw(sale);
        if (isFinite(c) && c > 0 && isFinite(s)) pct.value = fmtPct((s - c) / c * 100);
      }
    });
  })();
  (function tabs() {
    const btns = document.querySelectorAll(".tab-btn");
    btns.forEach((btn) => {
      btn.addEventListener("click", () => {
        btns.forEach((b) => b.classList.remove("active"));
        document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
        btn.classList.add("active");
        document.getElementById("tab-" + btn.getAttribute("data-tab")).classList.add("active");
      });
    });
  })();
  (function historyFilters() {
    const table = document.getElementById("intakeTable");
    if (!table) return;
    const search = document.getElementById("fltSearch");
    const fltProduct = document.getElementById("fltProduct");
    const fltPayType = document.getElementById("fltPayType");
    const countEl = document.getElementById("fltCount");
    const rows = table.querySelectorAll("tbody tr");
    function applyFilters() {
      const q = (search.value || "").toLowerCase();
      const prod = fltProduct.value;
      const pay = fltPayType.value;
      let visible = 0;
      rows.forEach((row) => {
        const matchesSearch = !q || (row.textContent || "").toLowerCase().indexOf(q) !== -1;
        const matchesProduct = !prod || row.getAttribute("data-product") === prod;
        const matchesPay = !pay || row.getAttribute("data-source") === pay;
        const show = matchesSearch && matchesProduct && matchesPay;
        row.style.display = show ? "" : "none";
        if (show) visible++;
      });
      countEl.textContent = window.T["sklad.showing_count"].replace("{total}", String(rows.length)).replace("{n}", String(visible));
    }
    search.addEventListener("input", applyFilters);
    fltProduct.addEventListener("change", applyFilters);
    fltPayType.addEventListener("change", applyFilters);
    applyFilters();
  })();
  (function intakeModal() {
    const modal = document.getElementById("intakeModal");
    const openBtn = document.getElementById("openIntakeBtn");
    const closeBtn = document.getElementById("closeIntakeBtn");
    const cancelBtn = document.getElementById("cancelIntakeBtn");
    const container = document.getElementById("intakeRows");
    const addBtn = document.getElementById("addIntakeRowBtn");
    const totalEl = document.getElementById("intakeTotal");
    if (!modal || !openBtn) return;
    function fmtMoney(n) {
      const parts = n.toFixed(2).split(".");
      parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, " ");
      return parts.join(".");
    }
    function updateRemoveButtons() {
      const rows = container.querySelectorAll(".intake-row");
      rows.forEach((row) => {
        row.querySelector(".intake-remove-btn").disabled = rows.length <= 1;
      });
    }
    function computeTotal() {
      const totals = {};
      container.querySelectorAll(".intake-row").forEach((row) => {
        const select = row.querySelector("select[name='product_id[]']");
        const qtyInput = row.querySelector("input[name='qty[]']");
        const opt = select.options[select.selectedIndex];
        if (!opt) return;
        const price = parseFloat(opt.getAttribute("data-price") || "0") || 0;
        const currency = opt.getAttribute("data-currency") || "UZS";
        const qty = parseFloat(qtyInput.value) || 0;
        totals[currency] = (totals[currency] || 0) + price * qty;
      });
      const parts = [];
      Object.keys(totals).forEach((cur) => {
        if (totals[cur]) parts.push(fmtMoney(totals[cur]) + " " + cur);
      });
      totalEl.textContent = `${window.T["bar.cart_total"]}: ` + (parts.length ? parts.join(" + ") : "0");
    }
    const statusSelect = document.getElementById("intakeStatus");
    const payTypeField = document.getElementById("intakePayTypeField");
    function updatePayTypeVisibility() {
      const unpaid = statusSelect.value === "unpaid";
      payTypeField.style.display = unpaid ? "none" : "";
    }
    statusSelect.addEventListener("change", updatePayTypeVisibility);
    openBtn.addEventListener("click", () => {
      modal.showModal();
      computeTotal();
      updatePayTypeVisibility();
    });
    closeBtn.addEventListener("click", () => modal.close());
    cancelBtn.addEventListener("click", () => modal.close());
    addBtn.addEventListener("click", () => {
      const rows = container.querySelectorAll(".intake-row");
      const clone = rows[rows.length - 1].cloneNode(true);
      clone.querySelector("input[name='qty[]']").value = "1";
      clone.querySelector(".intake-remove-btn").disabled = false;
      container.appendChild(clone);
      updateRemoveButtons();
      computeTotal();
    });
    container.addEventListener("click", (e) => {
      const target = e.target;
      if (target.classList.contains("intake-remove-btn") && !target.disabled) {
        target.closest(".intake-row").remove();
        updateRemoveButtons();
        computeTotal();
      }
    });
    container.addEventListener("input", computeTotal);
    container.addEventListener("change", computeTotal);
  })();
})();
