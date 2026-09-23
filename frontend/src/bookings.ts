// Ported 1:1 from templates/bookings.html's inline <script>: a client-side
// substring filter over the bookings table, plus a per-row expand toggle
// that reveals the extra Exely fields (taxes, services, cancellation, ...).
import "./types";

document.getElementById("searchBox")!.addEventListener("input", function (this: HTMLInputElement) {
  const q = this.value.toLowerCase();
  document.querySelectorAll<HTMLTableRowElement>("#bookingsTable tbody tr.booking-row").forEach((tr) => {
    const match = (tr.textContent || "").toLowerCase().includes(q);
    tr.style.display = match ? "" : "none";
    const detail = tr.nextElementSibling as HTMLTableRowElement | null;
    if (detail && detail.classList.contains("booking-detail") && !match) {
      detail.hidden = true;
      const btn = tr.querySelector<HTMLButtonElement>(".booking-expand");
      if (btn) { btn.setAttribute("aria-expanded", "false"); btn.textContent = "▸"; }
    }
  });
});

document.querySelectorAll<HTMLButtonElement>(".booking-expand").forEach((btn) => {
  btn.addEventListener("click", () => {
    const row = btn.closest("tr");
    const detail = row?.nextElementSibling as HTMLTableRowElement | null;
    if (!detail || !detail.classList.contains("booking-detail")) return;
    const open = detail.hidden;
    detail.hidden = !open;
    btn.setAttribute("aria-expanded", String(open));
    btn.textContent = open ? "▾" : "▸";
  });
});
