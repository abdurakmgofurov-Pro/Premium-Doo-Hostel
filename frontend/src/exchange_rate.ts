// Ported 1:1 from templates/exchange_rate.html's inline <script>: a
// hand-rolled SVG line chart (no charting library, by design -- this is
// meant to keep working fully offline). Rate history comes from a JSON
// data-island (#rateData) rather than window.RATE_DATA, matching the
// array-shaped-data convention used for roles.html.
import "./types";

interface RatePoint {
  date: string;
  uzs_per_usd: number | null;
  uzs_per_eur: number | null;
}

function buildRateChart(data: RatePoint[]): void {
  const wrap = document.getElementById("rateChart") as HTMLElement;
  if (!data || data.length === 0) return;
  const asc = [...data].sort((a, b) => a.date.localeCompare(b.date));
  const w = Math.max(700, asc.length * 70);
  const h = 280;
  const padL = 60;
  const padR = 20;
  const padT = 20;
  const padB = 34;
  const n = asc.length;
  const x = (i: number) => (n === 1 ? w / 2 : padL + (i / (n - 1)) * (w - padL - padR));

  const usdSeries = asc.map((d) => d.uzs_per_usd).filter((v): v is number => !!v);
  const eurSeries = asc.map((d) => d.uzs_per_eur).filter((v): v is number => !!v);
  const allValues = [...usdSeries, ...eurSeries];
  if (allValues.length === 0) return;
  const minV = Math.min(...allValues);
  const maxV = Math.max(...allValues);
  const rangeV = maxV - minV || 1;
  const y = (v: number) => h - padB - ((v - minV) / rangeV) * (h - padT - padB);

  function buildPath(field: "uzs_per_usd" | "uzs_per_eur"): string {
    const pts: [number, number][] = [];
    asc.forEach((d, i) => {
      const v = d[field];
      if (v) pts.push([x(i), y(v)]);
    });
    if (pts.length === 0) return "";
    let path = `M ${pts[0][0]},${pts[0][1]}`;
    for (let i = 1; i < pts.length; i++) {
      const [x0, y0] = pts[i - 1];
      const [x1, y1] = pts[i];
      const mx = (x0 + x1) / 2;
      const my = (y0 + y1) / 2;
      path += ` Q ${x0},${y0} ${mx},${my}`;
    }
    return path;
  }
  const usdPath = buildPath("uzs_per_usd");
  const eurPath = buildPath("uzs_per_eur");

  const yLabels = [minV, (minV + maxV) / 2, maxV].map((v) => Math.round(v));
  const xLabelEvery = Math.max(1, Math.ceil(n / 12));
  const xLabels = asc
    .map((d, i) =>
      i % xLabelEvery === 0 || i === n - 1
        ? `<text x="${x(i)}" y="${h - 8}" font-size="10" fill="var(--ink-secondary)" text-anchor="middle">${d.date}</text>`
        : "",
    )
    .join("");

  wrap.innerHTML = `
    <svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" style="height:280px;width:${w}px">
      <text x="4" y="${y(yLabels[2]) + 4}" font-size="10" fill="var(--ink-secondary)">${yLabels[2]}</text>
      <text x="4" y="${y(yLabels[1]) + 4}" font-size="10" fill="var(--ink-secondary)">${yLabels[1]}</text>
      <text x="4" y="${y(yLabels[0]) + 4}" font-size="10" fill="var(--ink-secondary)">${yLabels[0]}</text>
      ${usdPath ? `<path d="${usdPath}" fill="none" stroke="var(--accent-light)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>` : ""}
      ${eurPath ? `<path d="${eurPath}" fill="none" stroke="var(--good)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>` : ""}
      ${xLabels}
    </svg>`;
}

const dataEl = document.getElementById("rateData");
if (dataEl) {
  buildRateChart(JSON.parse(dataEl.textContent || "[]"));
}
