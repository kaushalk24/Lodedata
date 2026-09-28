/* Stylised front/back muscle map. Shapes are drawn for the figure's left half and mirrored.
 * Muscle regions get a class from their state (fresh/recovering/rested/none, or primary/secondary)
 * and, when interactive, data-a="muscle" so tapping opens that muscle. */
import { raw } from './util.js';

// [muscle | null (non-muscle skin), path]
const FRONT = [
  [null, 'M55 29 L65 29 L66.5 39 L53.5 39Z'],
  ['traps', 'M53.5 34.5 C49 38.5 44 40.5 38.5 41.8 L53.5 42.8 Z'],
  ['shoulders', 'M38 42.5 C30 43.5 26 49.5 26.5 58 C27 63 28.5 67 30.5 69.5 C33 62 36.5 56.5 43 53 C44 49 42 45.5 38 42.5 Z'],
  ['chest', 'M59 44.5 L45.2 44 C41.2 46.5 40.8 52.5 42.8 58.8 C45.6 66 52 69.2 59 68 Z'],
  ['triceps', 'M28.2 67.5 C26.2 75 26.2 84.5 28.2 93 L30.2 93.8 C29 86 28.8 77.5 30.3 71 Z'],
  ['biceps', 'M31 71 C29.6 78 29.6 86.5 31 94 L35.4 95 C38.4 88 40.2 80 40.4 72.5 C40 65.5 37.5 61.5 34.8 62.5 C33 64.5 31.7 67.5 31 71 Z'],
  ['forearms', 'M29 97.5 C25.2 106.5 23.2 118.5 22.6 131.5 L27.6 132.8 C31.2 122 35.2 110 37.2 98.5 C35.2 96.4 31.4 96.2 29 97.5 Z'],
  [null, 'M22.4 134.2 L27.6 135 L27.2 146 C26.4 150.4 23.2 151.2 21.6 148.2 L21 138.4 Z'],
  ['obliques', 'M42.8 63.5 C44.6 72 45.6 81 45.9 90.5 C46.3 100 47.4 108.5 49.4 116.5 L51.4 116.5 L51.4 71.5 C48 70.5 45.2 67.8 42.8 63.5 Z'],
  ['abs', 'rect 52.6 71 6.4 10.6'], ['abs', 'rect 52.6 83.5 6.4 10.6'], ['abs', 'rect 52.6 96 6.4 10.6'], ['abs', 'rect 53 108.5 6 11.5'],
  ['abductors', 'M41.6 118.5 C38.6 124.5 37.4 130.5 37.9 138.5 L41.9 136.5 C42 130.5 43.2 124.5 45.4 119.5 Z'],
  ['quads', 'M45.6 120.5 C40.4 130.5 38.4 148 39.2 165 C40 172 42 177 45 180.5 L52 180.5 C55 170 56.8 155 56 140.5 C55.2 131 52.6 124.5 49.4 120.5 Z'],
  ['adductors', 'M57.2 127.5 C58.4 135 58.8 142.5 58.3 150 C57.8 156 56.4 160.2 54.8 162.6 C56.2 150.5 56 138.5 53.2 129.5 Z'],
  [null, 'M44.8 182.5 L52.2 182.5 L51.6 188 L44.4 188 Z'],
  ['calves', 'M44.2 189.5 C41.4 199 41.2 211.5 43.2 224 L47.2 228 C49.2 216 50.8 204 50.8 193 C50.2 190.2 47.8 189.2 44.2 189.5 Z'],
  ['calves', 'M52.4 192.5 C54.2 201.5 54.2 212.5 52.3 222 L50.3 224.5 C50.4 212.5 51.2 201.5 52.4 192.5 Z'],
  [null, 'M43.2 229.5 L49.4 229.5 L50.4 238.5 L41 238.5 Z'],
];

const BACK = [
  [null, 'M55 29 L65 29 L66.5 36 L53.5 36Z'],
  ['traps', 'M60 30.5 L53.8 33.4 C48 37.2 43 40.2 38.6 42.2 L48.4 46.2 C52.6 52.6 56.4 61 60 73 Z'],
  ['shoulders', 'M38 42.8 C30 43.8 26 49.5 26.5 58 C27 63 28.5 67 30.5 69.5 C33 62 36.5 56.5 43 53.2 C44 49.2 42 45.8 38 42.8 Z'],
  ['back', 'M48 47.4 C44.2 50 42.4 53.6 42 57.6 C47.4 58.6 52.4 62.4 57.4 68.6 C55.4 60.6 52.2 53 48 47.4 Z'],
  ['back', 'M41.8 60 C42.6 72.6 45.8 86.4 51 98.4 L59 103.4 L59 75.6 C55.2 67.8 49.4 62 41.8 60 Z'],
  ['triceps', 'M31 71 C29.6 78 29.6 86.5 31 94 L35.4 95 C38.4 88 40.2 80 40.4 72.5 C40 65.5 37.5 61.5 34.8 62.5 C33 64.5 31.7 67.5 31 71 Z'],
  ['biceps', 'M28.2 67.5 C26.2 75 26.2 84.5 28.2 93 L30.2 93.8 C29 86 28.8 77.5 30.3 71 Z'],
  ['forearms', 'M29 97.5 C25.2 106.5 23.2 118.5 22.6 131.5 L27.6 132.8 C31.2 122 35.2 110 37.2 98.5 C35.2 96.4 31.4 96.2 29 97.5 Z'],
  [null, 'M22.4 134.2 L27.6 135 L27.2 146 C26.4 150.4 23.2 151.2 21.6 148.2 L21 138.4 Z'],
  ['lowerback', 'M59 105 L51.2 100.2 C49.4 105 48.6 110.4 49.4 116 L59 117.6 Z'],
  ['obliques', 'M42.2 70 C43.4 82 45.4 92 49.6 99.4 C48 104.6 47.4 109.6 47.8 113.2 L44.2 112.4 C42.6 100 41.8 85 42.2 70 Z'],
  ['abductors', 'M43.6 113.4 C40.4 117 39.2 121.6 39.8 127.4 C42 121.8 45.2 118.8 49.8 117.6 L48.8 114.2 Z'],
  ['glutes', 'M59 119.2 L49.6 118.4 C43.6 121 40.6 127.4 41 135.2 C41.4 142 46 146.4 52 146.6 C56 146.6 58.4 144.6 59.4 141.4 Z'],
  ['hamstrings', 'M41.4 147 C39.2 158.4 40 170.4 43.2 180.6 L50.2 181.4 C53.2 170.4 54.8 158.4 54.8 148.6 C51.8 148.6 46.2 148.4 41.4 147 Z'],
  ['adductors', 'M56 148 C58.6 151 59.1 158.6 58.1 166.4 C57.4 170.6 56.2 173.6 54.8 175.6 C56.2 165.6 56.8 155.6 56 148 Z'],
  [null, 'M44 183 L51.4 183 L51.2 187.4 L43.8 187.4 Z'],
  ['calves', 'M43.4 188.4 C40.4 198.4 40.8 208.6 43.6 218.4 C45.2 222.4 48.2 223.4 50.2 220.4 C52.2 210.4 52.6 198.4 51.2 189 C49.2 186.8 46.4 186.8 43.4 188.4 Z'],
  ['calves', 'M52.6 190 C55.4 198 55.8 208.2 53.2 218.2 L51.4 220.6 C52.8 208.4 53.4 198.4 52.6 190 Z'],
  [null, 'M43.2 225.5 L49.6 225.5 L50.4 238.5 L41 238.5 Z'],
];

function shape([m, d], cls, interactive) {
  const attrs = m ? `class="mu ${cls(m)}" data-m="${m}"${interactive ? ' data-a="muscle"' : ''}` : 'class="skin"';
  if (d.startsWith('rect')) {
    const [x, y, w, h] = d.slice(5).split(' ').map(Number);
    return `<rect ${attrs} x="${x}" y="${y}" width="${w}" height="${h}" rx="2.2"/>`;
  }
  return `<path ${attrs} d="${d}"/>`;
}

function figure(shapes, cls, interactive, label) {
  const half = shapes.map(s => shape(s, cls, interactive)).join('');
  return `<svg class="figure" viewBox="0 0 120 245" role="img" aria-label="${label}">
    <ellipse class="skin" cx="60" cy="17.5" rx="10.5" ry="13"/>
    <g>${half}</g><g transform="translate(120 0) scale(-1 1)">${half}</g></svg>`;
}

/**
 * @param {object} o
 * @param {(m:string)=>string} o.cls  muscle -> css class
 * @param {boolean} [o.interactive]
 * @param {boolean} [o.small]
 */
export function bodyMap({ cls, interactive = false, small = false }) {
  return raw(`<div class="bodymap${small ? ' small' : ''}">${figure(FRONT, cls, interactive, 'Front')}${figure(BACK, cls, interactive, 'Back')}</div>`);
}
