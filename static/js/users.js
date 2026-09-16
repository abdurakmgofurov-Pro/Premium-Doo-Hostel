"use strict";
(() => {
  // src/users.ts
  (function() {
    const dataEl = document.getElementById("usersData");
    if (!dataEl) return;
    const USERS = JSON.parse(dataEl.textContent || "[]");
    const modal = document.getElementById("userEditModal");
    const form = document.getElementById("userEditForm");
    document.querySelectorAll(".user-edit").forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = parseInt(btn.getAttribute("data-user-id") || "0", 10);
        const u = USERS.filter((x) => x.id === id)[0];
        if (!u) return;
        form.action = "/users/" + id + "/edit";
        document.getElementById("editFullName").value = u.full_name || "";
        document.getElementById("editRoleId").value = String(u.role_id || "");
        document.getElementById("editPassword").value = "";
        document.getElementById("editIsActive").checked = !!u.is_active;
        modal.showModal();
      });
    });
    document.getElementById("closeUserEditBtn").addEventListener("click", () => modal.close());
  })();
})();
