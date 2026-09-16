// Ported 1:1 from templates/users.html's inline <script>: the edit modal,
// driven by a JSON data-island (#usersData).
import "./types";

interface User {
  id: number;
  full_name: string | null;
  role_id: number | null;
  is_active: number | boolean;
}

(function () {
  const dataEl = document.getElementById("usersData");
  if (!dataEl) return;
  const USERS: User[] = JSON.parse(dataEl.textContent || "[]");
  const modal = document.getElementById("userEditModal") as HTMLDialogElement;
  const form = document.getElementById("userEditForm") as HTMLFormElement;

  document.querySelectorAll<HTMLButtonElement>(".user-edit").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = parseInt(btn.getAttribute("data-user-id") || "0", 10);
      const u = USERS.filter((x) => x.id === id)[0];
      if (!u) return;
      form.action = "/users/" + id + "/edit";
      (document.getElementById("editFullName") as HTMLInputElement).value = u.full_name || "";
      (document.getElementById("editRoleId") as HTMLSelectElement).value = String(u.role_id || "");
      (document.getElementById("editPassword") as HTMLInputElement).value = "";
      (document.getElementById("editIsActive") as HTMLInputElement).checked = !!u.is_active;
      modal.showModal();
    });
  });

  document.getElementById("closeUserEditBtn")!.addEventListener("click", () => modal.close());
})();
