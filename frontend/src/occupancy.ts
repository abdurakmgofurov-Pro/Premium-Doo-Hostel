// Xonalar → Bandlik grafigi. Server faqat ma'lumotni beradi (#occData);
// chizish brauzerda konteyner kengligiga MOSLAB bajariladi, shuning uchun
// yozuvlar keng/tor ekranda ham bir xil o'lchamda qoladi.
import "./types";

interface OccPoint {
  label: string;
  room_pct: number;
  bed_pct: number;
  rooms_occ: number;
  rooms_total: number;
  beds_occ: number;
  beds_total: number;
  ex_pct: number | null;
  ex_occ: number | null;
  ex_total: number | null;
}

interface OccData {
  series: OccPoint[];
  names: { room: string; bed: string; exely: string };
}

const SVG_NS = "http://www.w3.org/2000/svg";
const COLORS = { room: "var(--series-1)", bed: "var(--series-2)", exely: "var(--series-4)" };

function el<K extends keyof SVGElementTagNameMap>(tag: K, attrs: Record<string, string | number>): SVGElementTagNameMap[K] {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, String(v));
  return node;
}

function niceMax(series: OccPoint[]): number {
  const top = Math.max(100, ...series.flatMap((p) => [p.room_pct, p.bed_pct, p.ex_pct ?? 0]));
  return top <= 100 ? 100 : Math.ceil(top / 25) * 25; // overbooking bo'lsa o'q 100% dan yuqori chiqadi
}

function render(wrap: HTMLElement, tip: HTMLElement, data: OccData): void {
  const { series, names } = data;
  const n = series.length;
  if (n === 0) return;
  const width = Math.max(wrap.clientWidth, 320);
  const height = width < 520 ? 240 : 300;
  const padL = 44;
  const padR = 14;
  const padT = 14;
  const padB = 30;
  const plotW = width - padL - padR;
  const plotH = height - padT - padB;
  const yMax = niceMax(series);
  const x = (i: number) => (n === 1 ? padL + plotW / 2 : padL + (plotW * i) / (n - 1));
  const y = (pct: number) => padT + (1 - pct / yMax) * plotH;

  const svg = el("svg", { width, height, viewBox: `0 0 ${width} ${height}`, role: "img" });
  svg.style.display = "block";

  // gorizontal to'r
  for (let v = 0; v <= yMax; v += 25) {
    svg.append(el("line", { x1: padL, x2: padL + plotW, y1: y(v), y2: y(v), stroke: "var(--border)", "stroke-width": 1 }));
    const t = el("text", { x: padL - 8, y: y(v) + 4, "text-anchor": "end", "font-size": 11, fill: "var(--ink-muted)" });
    t.textContent = `${v}%`;
    svg.append(t);
  }
  if (yMax > 100) {
    svg.append(el("line", { x1: padL, x2: padL + plotW, y1: y(100), y2: y(100), stroke: "var(--ink-muted)", "stroke-width": 1, "stroke-dasharray": "4 4" }));
  }

  // x yozuvlari: bir-biriga tegmaydigan qadam bilan
  const every = Math.max(1, Math.ceil((n * 64) / plotW));
  for (let i = 0; i < n; i += every) {
    const raw = series[i].label;
    const t = el("text", { x: x(i), y: height - 9, "text-anchor": "middle", "font-size": 11, fill: "var(--ink-secondary)" });
    t.textContent = raw.length > 7 ? raw.slice(5) : raw;
    svg.append(t);
  }

  const lines: Array<[string, (p: OccPoint) => number | null, number]> = [
    [COLORS.bed, (p) => p.bed_pct, 2],
    [COLORS.room, (p) => p.room_pct, 2],
    [COLORS.exely, (p) => p.ex_pct, 2.6],
  ];
  const showDots = n <= 45;
  for (const [color, get, sw] of lines) {
    const pts: string[] = [];
    series.forEach((p, i) => {
      const v = get(p);
      if (v !== null) pts.push(`${x(i).toFixed(1)},${y(v).toFixed(1)}`);
    });
    if (pts.length === 0) continue;
    svg.append(el("polyline", { points: pts.join(" "), fill: "none", stroke: color, "stroke-width": sw, "stroke-linejoin": "round", "stroke-linecap": "round" }));
    if (showDots) {
      series.forEach((p, i) => {
        const v = get(p);
        if (v !== null) svg.append(el("circle", { cx: x(i), cy: y(v), r: 2.8, fill: color }));
      });
    }
  }

  // ustiga sichqoncha olib borilganda — eng yaqin nuqta bo'yicha ma'lumot
  const guide = el("line", { y1: padT, y2: padT + plotH, stroke: "var(--ink-muted)", "stroke-width": 1, "stroke-dasharray": "3 3", visibility: "hidden" });
  svg.append(guide);
  const hit = el("rect", { x: padL, y: padT, width: plotW, height: plotH, fill: "transparent" });
  svg.append(hit);

  const row = (color: string, name: string, pct: number, occ: number, total: number) =>
    `<div><i style="background:${color}"></i>${name}: <b>${pct}%</b> <span>(${occ}/${total})</span></div>`;

  hit.addEventListener("mousemove", (ev: MouseEvent) => {
    const box = svg.getBoundingClientRect();
    const rel = ev.clientX - box.left - padL;
    const i = Math.min(n - 1, Math.max(0, Math.round((rel / plotW) * (n - 1))));
    const p = series[i];
    guide.setAttribute("x1", String(x(i)));
    guide.setAttribute("x2", String(x(i)));
    guide.setAttribute("visibility", "visible");
    tip.innerHTML =
      `<strong>${p.label}</strong>` +
      row(COLORS.room, names.room, p.room_pct, p.rooms_occ, p.rooms_total) +
      row(COLORS.bed, names.bed, p.bed_pct, p.beds_occ, p.beds_total) +
      (p.ex_pct !== null ? row(COLORS.exely, names.exely, p.ex_pct, p.ex_occ ?? 0, p.ex_total ?? 0) : "");
    tip.hidden = false;
    const left = x(i) + 14 + tip.offsetWidth > width ? x(i) - 14 - tip.offsetWidth : x(i) + 14;
    tip.style.left = `${Math.max(left, 0)}px`;
    tip.style.top = `${padT + 6}px`;
  });
  hit.addEventListener("mouseleave", () => {
    tip.hidden = true;
    guide.setAttribute("visibility", "hidden");
  });

  wrap.replaceChildren(svg);
}

const wrap = document.getElementById("occChart");
const tip = document.getElementById("occTip");
const dataEl = document.getElementById("occData");
if (wrap && tip && dataEl) {
  const data = JSON.parse(dataEl.textContent || "{}") as OccData;
  const draw = () => render(wrap, tip, data);
  draw();
  let lastWidth = wrap.clientWidth;
  new ResizeObserver(() => {
    if (wrap.clientWidth !== lastWidth) {
      lastWidth = wrap.clientWidth;
      draw();
    }
  }).observe(wrap);
}
