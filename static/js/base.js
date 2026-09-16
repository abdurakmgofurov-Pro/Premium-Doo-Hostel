"use strict";
(() => {
  // src/base.ts
  function groupDigits(raw) {
    const parts = raw.split(".");
    let intPart = parts[0].replace(/\s/g, "");
    const decPart = parts.length > 1 ? parts.slice(1).join("") : null;
    intPart = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
    return decPart !== null ? intPart + "." + decPart : intPart;
  }
  document.addEventListener("input", (e) => {
    const el = e.target;
    if (!el.matches || !el.matches(".money-input")) return;
    const cursorFromEnd = el.value.length - (el.selectionStart ?? el.value.length);
    let raw = el.value.replace(/[^\d.]/g, "");
    const firstDot = raw.indexOf(".");
    if (firstDot !== -1) {
      raw = raw.slice(0, firstDot + 1) + raw.slice(firstDot + 1).replace(/\./g, "");
    }
    const newVal = groupDigits(raw);
    el.value = newVal;
    const pos = Math.max(0, newVal.length - cursorFromEnd);
    el.setSelectionRange(pos, pos);
  });
  document.addEventListener("submit", (e) => {
    const form = e.target;
    const fields = form.querySelectorAll ? form.querySelectorAll(".money-input") : [];
    fields.forEach((el) => {
      el.value = el.value.replace(/\s/g, "");
    });
  });
  document.addEventListener("submit", (e) => {
    const form = e.target;
    const msg = form.getAttribute && form.getAttribute("data-confirm");
    if (msg && !window.confirm(msg)) e.preventDefault();
  });
  document.addEventListener("submit", (e) => {
    const form = e.target;
    if (!form.method || form.method.toLowerCase() !== "post") return;
    if (form.querySelector('input[name="csrf_token"]')) return;
    const inp = document.createElement("input");
    inp.type = "hidden";
    inp.name = "csrf_token";
    inp.value = window.CSRF_TOKEN || "";
    form.appendChild(inp);
  });
})();
