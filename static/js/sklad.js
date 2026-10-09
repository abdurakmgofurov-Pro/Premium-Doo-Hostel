"use strict";
(() => {
  // src/sklad.ts
  function extractGtin(raw) {
    const m = raw.match(/^01(\d{14})/);
    return m ? m[1] : raw;
  }
  async function lookupBarcodeName(code) {
    try {
      const res = await fetch(`/bar/barcode_lookup/${encodeURIComponent(code)}`);
      if (!res.ok) return null;
      const data = await res.json();
      return data.name || null;
    } catch {
      return null;
    }
  }
  function suggestNewProduct(code, name) {
    const barcodeField = document.getElementById("addProductBarcode");
    const nameField = barcodeField?.closest("form")?.querySelector("[name=name]");
    if (!barcodeField || !nameField) return;
    barcodeField.value = code;
    if (!nameField.value.trim()) nameField.value = name;
    document.querySelector('.tab-btn[data-tab="products"]')?.click();
    nameField.scrollIntoView({ behavior: "smooth", block: "center" });
    nameField.focus();
  }
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
  (function addProductBarcodeScan() {
    const scanInput = document.getElementById("addProductBarcodeInput");
    const barcodeField = document.getElementById("addProductBarcode");
    const msgEl = document.getElementById("addProductBarcodeMsg");
    if (!scanInput || !barcodeField) return;
    const nameField = barcodeField.closest("form").querySelector("[name=name]");
    scanInput.addEventListener("keydown", async (e) => {
      if (e.key !== "Enter") return;
      e.preventDefault();
      const code = extractGtin(scanInput.value.trim());
      scanInput.value = "";
      if (!code) return;
      barcodeField.value = code;
      if (nameField && !nameField.value.trim()) {
        const name = await lookupBarcodeName(code);
        if (name && !nameField.value.trim()) {
          nameField.value = name;
          if (msgEl) msgEl.textContent = name;
        }
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
    function parsePrice(s) {
      const v = (s || "").replace(/\s/g, "");
      return v === "" ? NaN : parseFloat(v);
    }
    function fmtPct(n) {
      if (!isFinite(n)) return "";
      return (Math.round(n * 100) / 100).toString();
    }
    function updatePriceHint(row) {
      const select = row.querySelector("select[name='product_id[]']");
      const priceInput = row.querySelector(".intake-price-input");
      const marginInput = row.querySelector(".intake-margin-input");
      const salePriceInput = row.querySelector(".intake-sale-price-input");
      const opt = select.options[select.selectedIndex];
      if (!opt) return;
      const price = parseFloat(opt.getAttribute("data-price") || "0") || 0;
      const salePrice = parseFloat(opt.getAttribute("data-sale-price") || "0") || 0;
      priceInput.placeholder = window.T["sklad.current_price_hint"].replace("{price}", fmtMoney(price));
      salePriceInput.placeholder = window.T["sklad.current_price_hint"].replace("{price}", fmtMoney(salePrice));
      marginInput.placeholder = price > 0 ? fmtPct((salePrice - price) / price * 100) + "%" : "%";
    }
    function wireRowMarginCalc(row) {
      const costInput = row.querySelector(".intake-price-input");
      const marginInput = row.querySelector(".intake-margin-input");
      const saleInput = row.querySelector(".intake-sale-price-input");
      row.addEventListener("input", (e) => {
        const el = e.target;
        if (el !== costInput && el !== marginInput && el !== saleInput) return;
        const c = parsePrice(costInput.value);
        if (el === marginInput) {
          const p = parsePrice(marginInput.value);
          if (isFinite(c) && c > 0 && isFinite(p)) saleInput.value = fmtMoney(c * (1 + p / 100));
        } else if (el === costInput) {
          const p2 = parsePrice(marginInput.value);
          if (isFinite(c) && c > 0 && isFinite(p2)) saleInput.value = fmtMoney(c * (1 + p2 / 100));
        } else if (el === saleInput) {
          const s = parsePrice(saleInput.value);
          if (isFinite(c) && c > 0 && isFinite(s)) marginInput.value = fmtPct((s - c) / c * 100);
        }
      });
    }
    function computeTotal() {
      const totals = {};
      container.querySelectorAll(".intake-row").forEach((row) => {
        const select = row.querySelector("select[name='product_id[]']");
        const qtyInput = row.querySelector("input[name='qty[]']");
        const priceInput = row.querySelector(".intake-price-input");
        const opt = select.options[select.selectedIndex];
        if (!opt) return;
        const enteredPrice = parsePrice(priceInput.value);
        const price = isFinite(enteredPrice) ? enteredPrice : parseFloat(opt.getAttribute("data-price") || "0") || 0;
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
    const barcodeInput = document.getElementById("intakeBarcodeInput");
    const barcodeMsg = document.getElementById("intakeBarcodeMsg");
    wireRowMarginCalc(container.querySelector(".intake-row"));
    openBtn.addEventListener("click", () => {
      modal.showModal();
      container.querySelectorAll(".intake-row").forEach(updatePriceHint);
      computeTotal();
      barcodeInput?.focus();
    });
    closeBtn.addEventListener("click", () => modal.close());
    cancelBtn.addEventListener("click", () => modal.close());
    function addRow() {
      const rows = container.querySelectorAll(".intake-row");
      const clone = rows[rows.length - 1].cloneNode(true);
      clone.querySelector("input[name='qty[]']").value = "1";
      clone.querySelector(".intake-price-input").value = "";
      clone.querySelector(".intake-sale-price-input").value = "";
      clone.querySelector(".intake-margin-input").value = "";
      clone.querySelector(".intake-remove-btn").disabled = false;
      container.appendChild(clone);
      wireRowMarginCalc(clone);
      updatePriceHint(clone);
      updateRemoveButtons();
      return clone;
    }
    addBtn.addEventListener("click", () => {
      addRow();
      computeTotal();
    });
    if (barcodeInput && barcodeMsg) {
      const firstSelect = container.querySelector("select[name='product_id[]']");
      const byBarcode = {};
      Array.from(firstSelect.options).forEach((opt) => {
        const code = opt.getAttribute("data-barcode");
        if (code) byBarcode[code] = opt.value;
      });
      let msgTimer;
      const showMsg = (text, isError) => {
        barcodeMsg.textContent = text;
        barcodeMsg.className = "barcode-msg " + (isError ? "error" : "ok");
        window.clearTimeout(msgTimer);
        msgTimer = window.setTimeout(() => {
          barcodeMsg.textContent = "";
        }, 2500);
      };
      barcodeInput.addEventListener("keydown", async (e) => {
        if (e.key !== "Enter") return;
        e.preventDefault();
        const code = extractGtin(barcodeInput.value.trim());
        barcodeInput.value = "";
        if (!code) return;
        const productId = byBarcode[code];
        if (!productId) {
          const foundName = await lookupBarcodeName(code);
          if (foundName) {
            modal.close();
            suggestNewProduct(code, foundName);
          } else {
            showMsg(window.T["bar.barcode_not_found"], true);
            barcodeInput.focus();
          }
          return;
        }
        const existing = Array.from(container.querySelectorAll("select[name='product_id[]']")).find((sel) => sel.value === productId);
        let name = "";
        if (existing) {
          const row = existing.closest(".intake-row");
          const qtyInput = row.querySelector("input[name='qty[]']");
          qtyInput.value = String((parseFloat(qtyInput.value) || 0) + 1);
          name = existing.options[existing.selectedIndex].text;
        } else {
          const row = addRow();
          const select = row.querySelector("select[name='product_id[]']");
          select.value = productId;
          name = select.options[select.selectedIndex].text;
          updatePriceHint(row);
        }
        computeTotal();
        showMsg(name, false);
        barcodeInput.focus();
      });
    }
    container.addEventListener("click", (e) => {
      const target = e.target;
      if (target.classList.contains("intake-remove-btn") && !target.disabled) {
        target.closest(".intake-row").remove();
        updateRemoveButtons();
        computeTotal();
      }
    });
    container.addEventListener("input", computeTotal);
    container.addEventListener("change", (e) => {
      const target = e.target;
      if (target.matches("select[name='product_id[]']")) updatePriceHint(target.closest(".intake-row"));
      computeTotal();
    });
  })();
})();
