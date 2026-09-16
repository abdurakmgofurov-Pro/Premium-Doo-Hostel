"use strict";
(() => {
  // src/roles.ts
  (function() {
    const dataEl = document.getElementById("rolesData");
    if (!dataEl) return;
    const ROLES = JSON.parse(dataEl.textContent || "[]");
    const modal = document.getElementById("roleModal");
    const form = document.getElementById("roleForm");
    const title = document.getElementById("roleModalTitle");
    const nameInput = document.getElementById("roleNameInput");
    const descInput = document.getElementById("roleDescInput");
    const countEl = document.getElementById("selectedCount");
    const allActionBoxes = Array.prototype.slice.call(document.querySelectorAll(".mr-action"));
    const allSelectAllBoxes = Array.prototype.slice.call(document.querySelectorAll(".mr-select-all"));
    function updateCount() {
      countEl.textContent = String(allActionBoxes.filter((b) => b.checked).length);
    }
    function resetForm() {
      form.reset();
      allActionBoxes.forEach((b) => b.checked = false);
      allSelectAllBoxes.forEach((b) => b.checked = false);
      updateCount();
    }
    function openForNew() {
      resetForm();
      title.textContent = window.T["roles.modal_title_new"];
      form.action = "/roles/add";
      modal.showModal();
    }
    function openForEdit(role) {
      resetForm();
      title.textContent = `${window.T["roles.modal_title_edit"]}: ${role.name}`;
      form.action = "/roles/" + role.id + "/edit";
      nameInput.value = role.name;
      descInput.value = role.description || "";
      const perms = role.permissions || {};
      allActionBoxes.forEach((b) => {
        const mod = b.getAttribute("data-module");
        const action = b.name.split("__")[2];
        if (perms[mod] && perms[mod][action]) b.checked = true;
      });
      allSelectAllBoxes.forEach((b) => {
        const mod = b.getAttribute("data-module");
        const boxes = allActionBoxes.filter((x) => x.getAttribute("data-module") === mod && !x.disabled);
        b.checked = boxes.length > 0 && boxes.every((x) => x.checked);
      });
      updateCount();
      modal.showModal();
    }
    document.getElementById("newRoleBtn").addEventListener("click", openForNew);
    document.getElementById("closeRoleModalBtn").addEventListener("click", () => modal.close());
    document.getElementById("cancelRoleBtn").addEventListener("click", () => modal.close());
    document.querySelectorAll(".rc-edit").forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = parseInt(btn.getAttribute("data-role-id") || "0", 10);
        const role = ROLES.filter((r) => r.id === id)[0];
        if (role) openForEdit(role);
      });
    });
    allSelectAllBoxes.forEach((master) => {
      master.addEventListener("change", () => {
        const mod = master.getAttribute("data-module");
        allActionBoxes.forEach((b) => {
          if (b.getAttribute("data-module") === mod && !b.disabled) b.checked = master.checked;
        });
        updateCount();
      });
    });
    allActionBoxes.forEach((b) => b.addEventListener("change", updateCount));
  })();
})();
