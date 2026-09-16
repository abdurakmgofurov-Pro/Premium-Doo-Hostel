"use strict";
(() => {
  // src/settings.ts
  (function() {
    const input = document.getElementById("apiClientSecretInput");
    const btn = document.getElementById("toggleSecretBtn");
    if (!input || !btn) return;
    btn.addEventListener("click", () => {
      input.type = input.type === "password" ? "text" : "password";
    });
  })();
})();
