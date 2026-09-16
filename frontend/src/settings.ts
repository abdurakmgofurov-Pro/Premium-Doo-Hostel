// Ported 1:1 from templates/settings.html's inline <script>: the
// show/hide toggle for the Exely API client secret field (added earlier
// this session so the secret isn't shown in cleartext by default).
import "./types";

(function () {
  const input = document.getElementById("apiClientSecretInput") as HTMLInputElement | null;
  const btn = document.getElementById("toggleSecretBtn") as HTMLButtonElement | null;
  if (!input || !btn) return;
  btn.addEventListener("click", () => {
    input.type = input.type === "password" ? "text" : "password";
  });
})();
