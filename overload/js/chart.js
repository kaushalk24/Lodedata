/* Minimal SVG line chart: up to two series, each on its own scale (reps vs kg), evenly spaced
 * points, and touch/mouse scrubbing that shows the values under the finger. */
import { raw, esc } from './util.js';

const W = 340, H = 230, PAD = { l: 34, r: 34, t: 16, b: 26 };

/**
 * @param {{name:string, color:string, values:number[], fmt:(v:number)=>string}[]} series
 * @param {string[]} labels  x label per point (shown when scrubbing)
 */
export function lineChart(series, labels) {
  const n = labels.length;
  if (!n) return raw('<div class="chart-empty">Log a few sets to see a chart.</div>');
  const x = i => n === 1 ? (PAD.l + W - PAD.r) / 2 : PAD.l + (i * (W - PAD.l - PAD.r)) / (n - 1);
  const scales = series.map(s => {
    const vals = s.values.filter(v => v != null);
    let lo = Math.min(...vals), hi = Math.max(...vals);
    if (lo === hi) { lo -= 1; hi += 1; }
    const pad = (hi - lo) * 0.08; lo -= pad; hi += pad;
    return { lo, hi, y: v => PAD.t + (1 - (v - lo) / (hi - lo)) * (H - PAD.t - PAD.b) };
  });
  let body = '';
  for (let g = 0; g <= 4; g++) {
    const y = PAD.t + (g * (H - PAD.t - PAD.b)) / 4;
    body += `<line class="grid" x1="${PAD.l}" x2="${W - PAD.r}" y1="${y}" y2="${y}"/>`;
  }
  series.forEach((s, k) => {
    const sc = scales[k];
    const pts = s.values.map((v, i) => v == null ? null : [x(i), sc.y(v)]).filter(Boolean);
    const d = pts.map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(' ');
    if (pts.length > 1) {
      body += `<path d="${d} L${pts[pts.length - 1][0].toFixed(1)} ${H - PAD.b} L${pts[0][0].toFixed(1)} ${H - PAD.b} Z" fill="${s.color}" opacity="0.08"/>`;
    }
    body += `<path d="${d}" fill="none" stroke="${s.color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>`;
    if (n <= 40) body += pts.map(p => `<circle cx="${p[0].toFixed(1)}" cy="${p[1].toFixed(1)}" r="2.6" fill="var(--bg)" stroke="${s.color}" stroke-width="1.6"/>`).join('');
    const last = pts[pts.length - 1];
    if (last) body += `<circle cx="${last[0].toFixed(1)}" cy="${last[1].toFixed(1)}" r="4" fill="${s.color}"/>`;
    // axis labels: series 0 on the left, series 1 on the right, in the series colour
    const ax = k === 0 ? PAD.l - 6 : W - PAD.r + 6, anchor = k === 0 ? 'end' : 'start';
    const hiV = sc.hi - (sc.hi - sc.lo) * 0.08 / 1.16, loV = sc.lo + (sc.hi - sc.lo) * 0.08 / 1.16;
    body += `<text class="axis" x="${ax}" y="${sc.y(hiV) + 4}" text-anchor="${anchor}" fill="${s.color}">${esc(s.fmt(hiV))}</text>`;
    body += `<text class="axis" x="${ax}" y="${sc.y(loV) + 4}" text-anchor="${anchor}" fill="${s.color}">${esc(s.fmt(loV))}</text>`;
  });
  if (n > 1) {
    body += `<text class="axis muted" x="${PAD.l}" y="${H - 6}" text-anchor="start">${esc(labels[0])}</text>`;
    body += `<text class="axis muted" x="${W - PAD.r}" y="${H - 6}" text-anchor="end">${esc(labels[n - 1])}</text>`;
  }
  const data = { n, labels, xs: labels.map((_, i) => x(i)), series: series.map(s => ({ name: s.name, color: s.color, text: s.values.map(v => v == null ? '–' : s.fmt(v)) })) };
  return raw(`<div class="chart" data-chart='${esc(JSON.stringify(data))}'>
    <svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet">${body}<line class="scrub" x1="0" x2="0" y1="${PAD.t}" y2="${H - PAD.b}" visibility="hidden"/></svg>
    <div class="chart-tip" hidden></div></div>`);
}

/** Wire scrubbing for every chart inside `root`. */
export function hydrateCharts(root) {
  root.querySelectorAll('.chart[data-chart]').forEach(el => {
    if (el._wired) return; el._wired = true;
    const data = JSON.parse(el.dataset.chart);
    const svg = el.querySelector('svg'), line = el.querySelector('.scrub'), tip = el.querySelector('.chart-tip');
    const show = ev => {
      const r = svg.getBoundingClientRect();
      const vx = ((ev.clientX - r.left) / r.width) * W;
      let best = 0;
      data.xs.forEach((x, i) => { if (Math.abs(x - vx) < Math.abs(data.xs[best] - vx)) best = i; });
      line.setAttribute('x1', data.xs[best]); line.setAttribute('x2', data.xs[best]); line.setAttribute('visibility', 'visible');
      tip.hidden = false;
      tip.innerHTML = `<b>${esc(data.labels[best])}</b>` + data.series.map(s => `<span style="color:${s.color}">${esc(s.text[best])}</span>`).join('');
      const px = (data.xs[best] / W) * r.width;
      tip.style.left = `${Math.min(Math.max(px, 60), r.width - 60)}px`;
    };
    const hide = () => { line.setAttribute('visibility', 'hidden'); tip.hidden = true; };
    el.addEventListener('pointerdown', ev => { el.setPointerCapture?.(ev.pointerId); show(ev); });
    el.addEventListener('pointermove', ev => { if (ev.pointerType === 'mouse' || ev.buttons) show(ev); });
    el.addEventListener('pointerup', () => setTimeout(hide, 1200));
    el.addEventListener('pointerleave', ev => { if (ev.pointerType === 'mouse') hide(); });
  });
}
