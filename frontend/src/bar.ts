// Ported 1:1 from templates/bar.html's two inline <script> blocks: the
// edit-modal wiring, and the product-picker "cart" builder. `escapeHtml`
// guards against a real XSS bug (product name inserted into innerHTML
// after already being read back from a data-* attribute, which discards
// the attribute-context escaping Jinja applied) fixed earlier this
// session -- preserved exactly here.
import "./types";

interface CartProduct {
  name: string;
  price: number;
  currency: string;
  stock: number;
}

(function editModal() {
  const modal = document.getElementById("barEditModal") as HTMLDialogElement | null;
  if (!modal) return;
  const form = document.getElementById("barEditForm") as HTMLFormElement;
  document.querySelectorAll<HTMLButtonElement>(".bar-edit-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      form.action = "/bar/" + btn.getAttribute("data-id") + "/edit";
      (document.getElementById("editBarDate") as HTMLInputElement).value = btn.getAttribute("data-date") || "";
      (document.getElementById("editBarQty") as HTMLInputElement).value = btn.getAttribute("data-qty") || "";
      (document.getElementById("editBarSource") as HTMLSelectElement).value = btn.getAttribute("data-source") || "";
      (document.getElementById("editBarCounterparty") as HTMLInputElement).value = btn.getAttribute("data-counterparty") || "";
      (document.getElementById("editBarDescription") as HTMLInputElement).value = btn.getAttribute("data-description") || "";
      modal.showModal();
    });
  });
  document.getElementById("closeBarEditBtn")!.addEventListener("click", () => modal.close());
})();

(function cartBuilder() {
  const grid = document.getElementById("pickGrid");
  if (!grid) return;
  const cartRows = document.getElementById("cartRows") as HTMLElement;
  const cartEmpty = document.getElementById("cartEmpty") as HTMLElement;
  const totalEl = document.getElementById("cartTotal") as HTMLElement;
  const submitBtn = document.getElementById("sellSubmitBtn") as HTMLButtonElement;

  const products: Record<string, CartProduct> = {};
  grid.querySelectorAll<HTMLButtonElement>(".pick-card").forEach((card) => {
    const id = card.getAttribute("data-id")!;
    products[id] = {
      name: card.getAttribute("data-name") || "",
      price: parseFloat(card.getAttribute("data-price") || "0") || 0,
      currency: card.getAttribute("data-currency") || "UZS",
      stock: parseFloat(card.getAttribute("data-stock") || "0") || 0,
    };
  });

  const cart: Record<string, number> = {};

  function fmtMoney(n: number): string {
    const parts = n.toFixed(2).split(".");
    parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, " ");
    return parts.join(".");
  }

  function escapeHtml(s: string | null | undefined): string {
    const div = document.createElement("div");
    div.textContent = s == null ? "" : String(s);
    return div.innerHTML;
  }

  function removeRow(id: string): void {
    delete cart[id];
    const row = cartRows.querySelector(`.cart-row[data-id="${id}"]`);
    if (row) row.remove();
    const card = grid!.querySelector(`.pick-card[data-id="${id}"]`);
    if (card) card.classList.remove("selected");
    updateAll();
  }

  function buildRow(id: string): HTMLElement {
    const p = products[id];
    const row = document.createElement("div");
    row.className = "cart-row";
    row.setAttribute("data-id", id);
    row.innerHTML =
      `<input type="hidden" name="product_id[]" value="${id}">` +
      `<div class="cr-name">${escapeHtml(p.name)}</div>` +
      `<input type="number" class="cr-qty" name="qty[]" step="0.01" min="0.01"` +
      (p.stock ? ` max="${p.stock}"` : "") +
      ` value="${cart[id]}">` +
      `<div class="cr-sub"></div>` +
      `<button type="button" class="remove-row-btn">✕</button>`;
    row.querySelector(".cr-qty")!.addEventListener("input", (e) => {
      const v = parseFloat((e.target as HTMLInputElement).value);
      cart[id] = v > 0 ? v : 0;
      updateAll();
    });
    row.querySelector(".cr-qty")!.addEventListener("blur", (e) => {
      if (!(parseFloat((e.target as HTMLInputElement).value) > 0)) removeRow(id);
    });
    row.querySelector(".remove-row-btn")!.addEventListener("click", () => removeRow(id));
    return row;
  }

  function updateAll(): void {
    const ids = Object.keys(cart).filter((id) => cart[id] > 0);
    cartEmpty.style.display = ids.length ? "none" : "";
    const totals: Record<string, number> = {};
    ids.forEach((id) => {
      const p = products[id];
      const sub = p.price * cart[id];
      totals[p.currency] = (totals[p.currency] || 0) + sub;
      const row = cartRows.querySelector(`.cart-row[data-id="${id}"]`);
      if (row) (row.querySelector(".cr-sub") as HTMLElement).textContent = fmtMoney(sub) + " " + p.currency;
    });
    const parts: string[] = [];
    Object.keys(totals).forEach((cur) => {
      if (totals[cur]) parts.push(fmtMoney(totals[cur]) + " " + cur);
    });
    totalEl.textContent = `${window.T["bar.cart_total"]}: ` + (parts.length ? parts.join(" + ") : "0");
    submitBtn.disabled = ids.length === 0;
  }

  grid.querySelectorAll<HTMLButtonElement>(".pick-card").forEach((card) => {
    card.addEventListener("click", () => {
      if (card.disabled) return;
      const id = card.getAttribute("data-id")!;
      if (cart[id] > 0) {
        cart[id] += 1;
        const row = cartRows.querySelector(`.cart-row[data-id="${id}"]`);
        if (row) (row.querySelector(".cr-qty") as HTMLInputElement).value = String(cart[id]);
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
