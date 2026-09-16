// Ported 1:1 from templates/bookings.html's inline <script>: a client-side
// substring filter over the bookings table.
import "./types";

document.getElementById("searchBox")!.addEventListener("input", function (this: HTMLInputElement) {
  const q = this.value.toLowerCase();
  document.querySelectorAll<HTMLTableRowElement>("#bookingsTable tbody tr").forEach((tr) => {
    tr.style.display = (tr.textContent || "").toLowerCase().includes(q) ? "" : "none";
  });
});
