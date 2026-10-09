// Ported 1:1 from templates/sklad.html's inline <script>: margin%/sale-price
// auto-calculation, product/intake tabs, intake-history filters, and the
// multi-row "intake" (restock) modal.
import "./types";

// GS1 DataMatrix (2D) kodlar "01" + 14 xonali GTIN bilan boshlanadi va undan
// keyin har bir qadoqda boshqacha bo'ladigan seriya raqami keladi (masalan,
// O'zbekistondagi "Asl belgisi" markirovkasi). Takroriy skanerlashda mahsulot
// to'g'ri topilishi uchun faqat GTIN qismini shtrix-kod sifatida ishlatamiz.
function extractGtin(raw: string): string {
  const m = raw.match(/^01(\d{14})/);
  return m ? m[1] : raw;
}

// Lokal katalogda topilmagan shtrix-kodni Open Food Facts (ochiq mahsulotlar
// bazasi) orqali qidiradi, topilsa mahsulot nomini qaytaradi.
async function lookupBarcodeName(code: string): Promise<string | null> {
  try {
    const res = await fetch(`/bar/barcode_lookup/${encodeURIComponent(code)}`);
    if (!res.ok) return null;
    const data = await res.json();
    return data.name || null;
  } catch {
    return null;
  }
}

// Kirim oynasida shtrix-kod katalogda topilmasa, ochiq bazadan nomini qidirib,
// "Yangi mahsulot qo'shish" formasiga (nomi + shtrix-kodi bilan) o'tkazadi.
function suggestNewProduct(code: string, name: string): void {
  const barcodeField = document.getElementById("addProductBarcode") as HTMLInputElement | null;
  const nameField = barcodeField?.closest("form")?.querySelector<HTMLInputElement>("[name=name]");
  if (!barcodeField || !nameField) return;
  barcodeField.value = code;
  if (!nameField.value.trim()) nameField.value = name;
  document.querySelector<HTMLButtonElement>('.tab-btn[data-tab="products"]')?.click();
  nameField.scrollIntoView({ behavior: "smooth", block: "center" });
  nameField.focus();
}

(function marginCalc() {
  function raw(el: HTMLInputElement | null): number {
    if (!el) return NaN;
    const v = (el.value || "").replace(/\s/g, "");
    return v === "" ? NaN : parseFloat(v);
  }
  function fmtMoney(n: number): string {
    if (!isFinite(n)) return "";
    const parts = n.toFixed(2).split(".");
    parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, " ");
    return parts.join(".");
  }
  function fmtPct(n: number): string {
    if (!isFinite(n)) return "";
    return (Math.round(n * 100) / 100).toString();
  }
  document.addEventListener("input", (e: Event) => {
    const el = e.target as HTMLInputElement;
    const form = el.closest ? el.closest("form") : null;
    if (!form) return;
    const cost = form.querySelector<HTMLInputElement>("[name=cost_price]");
    const sale = form.querySelector<HTMLInputElement>("[name=sale_price]");
    const pct = form.querySelector<HTMLInputElement>(".margin-pct-input");
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
      if (isFinite(c) && c > 0 && isFinite(s)) pct.value = fmtPct(((s - c) / c) * 100);
    }
  });
})();

// "Yangi mahsulot qo'shish" formasidagi skanerlash maydoni: kodni GTIN'ga
// qisqartirib, to'g'ridan-to'g'ri SHTRIX-KOD maydoniga yozadi.
(function addProductBarcodeScan() {
  const scanInput = document.getElementById("addProductBarcodeInput") as HTMLInputElement | null;
  const barcodeField = document.getElementById("addProductBarcode") as HTMLInputElement | null;
  const msgEl = document.getElementById("addProductBarcodeMsg") as HTMLElement | null;
  if (!scanInput || !barcodeField) return;
  const nameField = barcodeField.closest("form")!.querySelector<HTMLInputElement>("[name=name]");
  scanInput.addEventListener("keydown", async (e: KeyboardEvent) => {
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

// Tabs
(function tabs() {
  const btns = document.querySelectorAll<HTMLButtonElement>(".tab-btn");
  btns.forEach((btn) => {
    btn.addEventListener("click", () => {
      btns.forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById("tab-" + btn.getAttribute("data-tab"))!.classList.add("active");
    });
  });
})();

// Intake history filters
(function historyFilters() {
  const table = document.getElementById("intakeTable") as HTMLTableElement | null;
  if (!table) return;
  const search = document.getElementById("fltSearch") as HTMLInputElement;
  const fltProduct = document.getElementById("fltProduct") as HTMLSelectElement;
  const fltPayType = document.getElementById("fltPayType") as HTMLSelectElement;
  const countEl = document.getElementById("fltCount") as HTMLElement;
  const rows = table.querySelectorAll<HTMLTableRowElement>("tbody tr");

  function applyFilters(): void {
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
    countEl.textContent = window.T["sklad.showing_count"]
      .replace("{total}", String(rows.length))
      .replace("{n}", String(visible));
  }

  search.addEventListener("input", applyFilters);
  fltProduct.addEventListener("change", applyFilters);
  fltPayType.addEventListener("change", applyFilters);
  applyFilters();
})();

// Intake modal
(function intakeModal() {
  const modal = document.getElementById("intakeModal") as HTMLDialogElement | null;
  const openBtn = document.getElementById("openIntakeBtn") as HTMLButtonElement | null;
  const closeBtn = document.getElementById("closeIntakeBtn") as HTMLButtonElement;
  const cancelBtn = document.getElementById("cancelIntakeBtn") as HTMLButtonElement;
  const container = document.getElementById("intakeRows") as HTMLElement;
  const addBtn = document.getElementById("addIntakeRowBtn") as HTMLButtonElement;
  const totalEl = document.getElementById("intakeTotal") as HTMLElement;
  if (!modal || !openBtn) return;

  function fmtMoney(n: number): string {
    const parts = n.toFixed(2).split(".");
    parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, " ");
    return parts.join(".");
  }

  function updateRemoveButtons(): void {
    const rows = container.querySelectorAll(".intake-row");
    rows.forEach((row) => {
      (row.querySelector(".intake-remove-btn") as HTMLButtonElement).disabled = rows.length <= 1;
    });
  }

  function parsePrice(s: string): number {
    const v = (s || "").replace(/\s/g, "");
    return v === "" ? NaN : parseFloat(v);
  }

  // Narx maydoni bo'sh qoldirilsa, mahsulotning joriy tan narxi ishlatiladi
  // (narx har safar kirimda o'zgarishi mumkin bo'lgani uchun, kiritilsa shu
  // yangi narx ishlatiladi va mahsulotning joriy narxi ham shunga yangilanadi).
  function updatePriceHint(row: Element): void {
    const select = row.querySelector<HTMLSelectElement>("select[name='product_id[]']")!;
    const priceInput = row.querySelector<HTMLInputElement>(".intake-price-input")!;
    const salePriceInput = row.querySelector<HTMLInputElement>(".intake-sale-price-input")!;
    const opt = select.options[select.selectedIndex];
    if (!opt) return;
    const price = parseFloat(opt.getAttribute("data-price") || "0") || 0;
    const salePrice = parseFloat(opt.getAttribute("data-sale-price") || "0") || 0;
    priceInput.placeholder = window.T["sklad.current_price_hint"].replace("{price}", fmtMoney(price));
    salePriceInput.placeholder = window.T["sklad.current_price_hint"].replace("{price}", fmtMoney(salePrice));
  }

  function computeTotal(): void {
    const totals: Record<string, number> = {};
    container.querySelectorAll(".intake-row").forEach((row) => {
      const select = row.querySelector<HTMLSelectElement>("select[name='product_id[]']")!;
      const qtyInput = row.querySelector<HTMLInputElement>("input[name='qty[]']")!;
      const priceInput = row.querySelector<HTMLInputElement>(".intake-price-input")!;
      const opt = select.options[select.selectedIndex];
      if (!opt) return;
      const enteredPrice = parsePrice(priceInput.value);
      const price = isFinite(enteredPrice) ? enteredPrice : parseFloat(opt.getAttribute("data-price") || "0") || 0;
      const currency = opt.getAttribute("data-currency") || "UZS";
      const qty = parseFloat(qtyInput.value) || 0;
      totals[currency] = (totals[currency] || 0) + price * qty;
    });
    const parts: string[] = [];
    Object.keys(totals).forEach((cur) => {
      if (totals[cur]) parts.push(fmtMoney(totals[cur]) + " " + cur);
    });
    totalEl.textContent = `${window.T["bar.cart_total"]}: ` + (parts.length ? parts.join(" + ") : "0");
  }

  const statusSelect = document.getElementById("intakeStatus") as HTMLSelectElement;
  const payTypeField = document.getElementById("intakePayTypeField") as HTMLElement;
  function updatePayTypeVisibility(): void {
    const unpaid = statusSelect.value === "unpaid";
    payTypeField.style.display = unpaid ? "none" : "";
  }
  statusSelect.addEventListener("change", updatePayTypeVisibility);

  const barcodeInput = document.getElementById("intakeBarcodeInput") as HTMLInputElement | null;
  const barcodeMsg = document.getElementById("intakeBarcodeMsg") as HTMLElement | null;

  openBtn.addEventListener("click", () => {
    modal.showModal();
    container.querySelectorAll(".intake-row").forEach(updatePriceHint);
    computeTotal();
    updatePayTypeVisibility();
    barcodeInput?.focus();
  });
  closeBtn.addEventListener("click", () => modal.close());
  cancelBtn.addEventListener("click", () => modal.close());

  function addRow(): HTMLElement {
    const rows = container.querySelectorAll(".intake-row");
    const clone = rows[rows.length - 1].cloneNode(true) as HTMLElement;
    (clone.querySelector("input[name='qty[]']") as HTMLInputElement).value = "1";
    (clone.querySelector(".intake-price-input") as HTMLInputElement).value = "";
    (clone.querySelector(".intake-sale-price-input") as HTMLInputElement).value = "";
    (clone.querySelector(".intake-remove-btn") as HTMLButtonElement).disabled = false;
    container.appendChild(clone);
    updatePriceHint(clone);
    updateRemoveButtons();
    return clone;
  }

  addBtn.addEventListener("click", () => {
    addRow();
    computeTotal();
  });

  // Shtrix-kod skaneri: topilgan mahsulot bilan qator qo'shadi (yoki shu mahsulot
  // allaqachon qatorda bo'lsa — miqdorini +1 qiladi), skaner klaviatura sifatida
  // ishlab, kod oxirida Enter yuboradi.
  if (barcodeInput && barcodeMsg) {
    const firstSelect = container.querySelector<HTMLSelectElement>("select[name='product_id[]']")!;
    const byBarcode: Record<string, string> = {};
    Array.from(firstSelect.options).forEach((opt) => {
      const code = opt.getAttribute("data-barcode");
      if (code) byBarcode[code] = opt.value;
    });
    let msgTimer: number | undefined;
    const showMsg = (text: string, isError: boolean) => {
      barcodeMsg.textContent = text;
      barcodeMsg.className = "barcode-msg " + (isError ? "error" : "ok");
      window.clearTimeout(msgTimer);
      msgTimer = window.setTimeout(() => {
        barcodeMsg.textContent = "";
      }, 2500);
    };
    barcodeInput.addEventListener("keydown", async (e: KeyboardEvent) => {
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
      const existing = Array.from(container.querySelectorAll<HTMLSelectElement>("select[name='product_id[]']"))
        .find((sel) => sel.value === productId);
      let name = "";
      if (existing) {
        const row = existing.closest(".intake-row") as HTMLElement;
        const qtyInput = row.querySelector<HTMLInputElement>("input[name='qty[]']")!;
        qtyInput.value = String((parseFloat(qtyInput.value) || 0) + 1);
        name = existing.options[existing.selectedIndex].text;
      } else {
        const row = addRow();
        const select = row.querySelector<HTMLSelectElement>("select[name='product_id[]']")!;
        select.value = productId;
        name = select.options[select.selectedIndex].text;
        updatePriceHint(row);
      }
      computeTotal();
      showMsg(name, false);
      barcodeInput.focus();
    });
  }

  container.addEventListener("click", (e: Event) => {
    const target = e.target as HTMLElement;
    if (target.classList.contains("intake-remove-btn") && !(target as HTMLButtonElement).disabled) {
      target.closest(".intake-row")!.remove();
      updateRemoveButtons();
      computeTotal();
    }
  });

  container.addEventListener("input", computeTotal);
  container.addEventListener("change", (e: Event) => {
    const target = e.target as HTMLElement;
    if (target.matches("select[name='product_id[]']")) updatePriceHint(target.closest(".intake-row")!);
    computeTotal();
  });
})();
