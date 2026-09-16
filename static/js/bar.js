"use strict";
(() => {
  // src/bar.ts
  (function editModal() {
    const modal = document.getElementById("barEditModal");
    if (!modal) return;
    const form = document.getElementById("barEditForm");
    document.querySelectorAll(".bar-edit-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        form.action = "/bar/" + btn.getAttribute("data-id") + "/edit";
        document.getElementById("editBarDate").value = btn.getAttribute("data-date") || "";
        document.getElementById("editBarQty").value = btn.getAttribute("data-qty") || "";
        document.getElementById("editBarSource").value = btn.getAttribute("data-source") || "";
        document.getElementById("editBarCounterparty").value = btn.getAttribute("data-counterparty") || "";
        document.getElementById("editBarDescription").value = btn.getAttribute("data-description") || "";
        modal.showModal();
      });
    });
    document.getElementById("closeBarEditBtn").addEventListener("click", () => modal.close());
  })();
  (function cartBuilder() {
    const grid = document.getElementById("pickGrid");
    if (!grid) return;
    const cartRows = document.getElementById("cartRows");
    const cartEmpty = document.getElementById("cartEmpty");
    const totalEl = document.getElementById("cartTotal");
    const submitBtn = document.getElementById("sellSubmitBtn");
    const products = {};
    grid.querySelectorAll(".pick-card").forEach((card) => {
      const id = card.getAttribute("data-id");
      products[id] = {
        name: card.getAttribute("data-name") || "",
        price: parseFloat(card.getAttribute("data-price") || "0") || 0,
        currency: card.getAttribute("data-currency") || "UZS",
        stock: parseFloat(card.getAttribute("data-stock") || "0") || 0
      };
    });
    const cart = {};
    function fmtMoney(n) {
      const parts = n.toFixed(2).split(".");
      parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, " ");
      return parts.join(".");
    }
    function escapeHtml(s) {
      const div = document.createElement("div");
      div.textContent = s == null ? "" : String(s);
      return div.innerHTML;
    }
    function removeRow(id) {
      delete cart[id];
      const row = cartRows.querySelector(`.cart-row[data-id="${id}"]`);
      if (row) row.remove();
      const card = grid.querySelector(`.pick-card[data-id="${id}"]`);
      if (card) card.classList.remove("selected");
      updateAll();
    }
    function buildRow(id) {
      const p = products[id];
      const row = document.createElement("div");
      row.className = "cart-row";
      row.setAttribute("data-id", id);
      row.innerHTML = `<input type="hidden" name="product_id[]" value="${id}"><div class="cr-name">${escapeHtml(p.name)}</div><input type="number" class="cr-qty" name="qty[]" step="0.01" min="0.01"` + (p.stock ? ` max="${p.stock}"` : "") + ` value="${cart[id]}"><div class="cr-sub"></div><button type="button" class="remove-row-btn">\u2715</button>`;
      row.querySelector(".cr-qty").addEventListener("input", (e) => {
        const v = parseFloat(e.target.value);
        cart[id] = v > 0 ? v : 0;
        updateAll();
      });
      row.querySelector(".cr-qty").addEventListener("blur", (e) => {
        if (!(parseFloat(e.target.value) > 0)) removeRow(id);
      });
      row.querySelector(".remove-row-btn").addEventListener("click", () => removeRow(id));
      return row;
    }
    function updateAll() {
      const ids = Object.keys(cart).filter((id) => cart[id] > 0);
      cartEmpty.style.display = ids.length ? "none" : "";
      const totals = {};
      ids.forEach((id) => {
        const p = products[id];
        const sub = p.price * cart[id];
        totals[p.currency] = (totals[p.currency] || 0) + sub;
        const row = cartRows.querySelector(`.cart-row[data-id="${id}"]`);
        if (row) row.querySelector(".cr-sub").textContent = fmtMoney(sub) + " " + p.currency;
      });
      const parts = [];
      Object.keys(totals).forEach((cur) => {
        if (totals[cur]) parts.push(fmtMoney(totals[cur]) + " " + cur);
      });
      totalEl.textContent = `${window.T["bar.cart_total"]}: ` + (parts.length ? parts.join(" + ") : "0");
      submitBtn.disabled = ids.length === 0;
    }
    grid.querySelectorAll(".pick-card").forEach((card) => {
      card.addEventListener("click", () => {
        if (card.disabled) return;
        const id = card.getAttribute("data-id");
        if (cart[id] > 0) {
          cart[id] += 1;
          const row = cartRows.querySelector(`.cart-row[data-id="${id}"]`);
          if (row) row.querySelector(".cr-qty").value = String(cart[id]);
        } else {
          cart[id] = 1;
          cartRows.appendChild(buildRow(id));
          card.classList.add("selected");
        }
        updateAll();
      });
    });
    updateAll();
  })();
})();
