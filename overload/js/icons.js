/* Hand-drawn 24px stroke icons (currentColor). `fill: true` icons are solid shapes. */
import { raw } from './util.js';

const P = {
  plus: 'M12 5v14M5 12h14',
  minus: 'M5 12h14',
  chevronRight: 'M9 6l6 6-6 6',
  chevronLeft: 'M15 5l-7 7 7 7',
  chevronDown: 'M6 9l6 6 6-6',
  updown: 'M8 9.5l4-4 4 4M8 14.5l4 4 4-4',
  x: 'M6 6l12 12M18 6L6 18',
  check: 'M5 12.5l4.5 4.5L19 7.5',
  gear: 'M12 8.8a3.2 3.2 0 1 0 0 6.4 3.2 3.2 0 0 0 0-6.4zM10.3 3h3.4l.5 2.4 1.7.9 2.3-.9 1.7 2.9-1.8 1.6v2.2l1.8 1.6-1.7 2.9-2.3-.9-1.7.9-.5 2.4h-3.4l-.5-2.4-1.7-.9-2.3.9-1.7-2.9 1.8-1.6v-2.2L3.9 8.3l1.7-2.9 2.3.9 1.7-.9z',
  flame: 'M12 21a6 6 0 0 0 6-6c0-4-3-6.5-4.5-10-1 2.5-1.5 4-3.5 5.5-.5-1-.8-2-.8-3C7 9 6 11.5 6 15a6 6 0 0 0 6 6zM12 21a2.5 2.5 0 0 1-2.5-2.5c0-1.6 1.3-2.4 2.5-4 1.2 1.6 2.5 2.4 2.5 4A2.5 2.5 0 0 1 12 21z',
  wand: 'M4 20L15 9M13 7l4 4M17.5 3v3M16 4.5h3M20.5 8v2M19.5 9h2M9 3.5v2M8 4.5h2',
  books: 'M4 4.5h3.5v15H4zM9.5 4.5H13v15H9.5zM15 5.6l3.2-.9 3.3 14.3-3.2.8z',
  book: 'M6 3.5h11.5v14H7.5A1.5 1.5 0 0 0 6 19v-15.5zM6 19a1.5 1.5 0 0 0 1.5 1.5h10v-3',
  search: 'M10.5 4a6.5 6.5 0 1 1 0 13 6.5 6.5 0 0 1 0-13zM15.5 15.5L20 20',
  share: 'M12 3.5V15M8 7.5l4-4 4 4M6 11H5v9h14v-9h-1',
  chart: 'M4 4v16h16M7.5 14.5l3.5-4 3 2.5 5-6',
  sun: 'M12 8.5a3.5 3.5 0 1 1 0 7 3.5 3.5 0 0 1 0-7zM12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4',
  trophy: 'M8 4h8v5.5a4 4 0 0 1-8 0zM8 6H5.5a2.5 2.5 0 0 0 2.6 3.8M16 6h2.5a2.5 2.5 0 0 1-2.6 3.8M12 13.5V17M8.5 20.5h7M9.5 17h5v3.5h-5z',
  filter: 'M4 7h16M7 12h10M10 17h4',
  layers: 'M12 4l8.5 4.2L12 12.4 3.5 8.2zM3.5 12L12 16.2l8.5-4.2M3.5 15.8L12 20l8.5-4.2',
  tag: 'M3.5 12.3V4.5a1 1 0 0 1 1-1h7.8l8.2 8.2a1 1 0 0 1 0 1.4l-7.4 7.4a1 1 0 0 1-1.4 0zM8 7.2a.8.8 0 1 1 0 1.6.8.8 0 0 1 0-1.6z',
  plate: 'M12 3.5a8.5 8.5 0 1 1 0 17 8.5 8.5 0 0 1 0-17zM12 9.5a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5z',
  person: 'M12 3a2 2 0 1 1 0 4 2 2 0 0 1 0-4zM4.5 9.5l7.5 1.5 7.5-1.5M12 11v4.5M12 15.5l-3 5.5M12 15.5l3 5.5',
  scale: 'M8.5 8a3.5 3.5 0 0 1 7 0M5.5 9.5h13l1.5 10.5H4z',
  calendar: 'M4 6.5h16v13.5H4zM4 10.5h16M8.5 3.5v5M15.5 3.5v5',
  backspace: 'M9 5.5h11.5v13H9l-6-6.5zM12.5 9.5l5 5M17.5 9.5l-5 5',
  keyboard: 'M3 6.5h18v10H3zM6.5 9.5h1M10 9.5h1M13.5 9.5h1M17 9.5h.5M7 13.5h10M10 20l2 1.5 2-1.5',
  forward: 'M14 5.5l6 6-6 6M20 11.5h-9a6 6 0 0 0-6 6V19',
  trash: 'M4.5 7h15M9.5 7V4.5h5V7M6.5 7l1 13h9l1-13M10 11v5.5M14 11v5.5',
  copy: 'M9 9h11v11H9zM15 9V4H4v11h5',
  note: 'M6 3.5h8.5l4 4v13H6zM14 3.5v4.5h4.5M9 12h6.5M9 16h4.5',
  refresh: 'M19.5 12a7.5 7.5 0 1 1-2.2-5.3M19.5 4.5V9H15',
  warning: 'M12 3.5l9.5 16.5h-19zM12 10v4.5M12 17.2v.3',
  pin: 'M12 21s-6.5-5.9-6.5-11a6.5 6.5 0 0 1 13 0c0 5.1-6.5 11-6.5 11zM12 7.5a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5z',
  timer: 'M12 5.5a7.5 7.5 0 1 1 0 15 7.5 7.5 0 0 1 0-15zM12 9.5V13l2.5 1.5M9.5 2.5h5M18.5 6l1.5-1.5',
  info: 'M12 3.5a8.5 8.5 0 1 1 0 17 8.5 8.5 0 0 1 0-17zM9.7 9.6a2.4 2.4 0 1 1 3.3 2.2c-.7.3-1 .8-1 1.5v.5M12 16.6v.4',
  edit: 'M4.5 19.5h4L19 9l-4-4L4.5 15.5zM13.5 6.5l4 4',
  up: 'M12 19V5M6.5 10.5L12 5l5.5 5.5',
  down: 'M12 5v14M6.5 13.5L12 19l5.5-5.5',
  download: 'M12 4v11M7.5 10.5L12 15l4.5-4.5M5 19.5h14',
  upload: 'M12 15.5V4.5M7.5 9L12 4.5 16.5 9M5 19.5h14',
  crown: 'M4 8l4 4 4-7 4 7 4-4-1.5 10.5h-13z',
  heart: 'M12 20s-7.5-4.6-7.5-10A4.3 4.3 0 0 1 12 7.3 4.3 4.3 0 0 1 19.5 10c0 5.4-7.5 10-7.5 10z',
  bolt: 'M13 3L5.5 13.5H12L11 21l7.5-10.5H12z',
  target: 'M12 3.5a8.5 8.5 0 1 1 0 17 8.5 8.5 0 0 1 0-17zM12 8a4 4 0 1 1 0 8 4 4 0 0 1 0-8zM12 11.3a.7.7 0 1 1 0 1.4.7.7 0 0 1 0-1.4z',
  moon: 'M19.5 14.5A8 8 0 0 1 9.5 4.5a8 8 0 1 0 10 10z',
  palette: 'M12 3.5a8.5 8.5 0 0 0 0 17c1.2 0 1.8-.8 1.8-1.7 0-1.2-1-1.5-1-2.6 0-1 .8-1.7 1.8-1.7h2.2a3.7 3.7 0 0 0 3.7-3.7c0-4.2-3.8-7.3-8.5-7.3zM7.5 12a1 1 0 1 1 0 .1zM9.5 8a1 1 0 1 1 0 .1zM14.5 8a1 1 0 1 1 0 .1z',
  bell: 'M6 16.5V11a6 6 0 0 1 12 0v5.5l1.5 2h-15zM10 20.5a2 2 0 0 0 4 0',
  database: 'M12 3.5c4.1 0 7.5 1.3 7.5 3s-3.4 3-7.5 3-7.5-1.3-7.5-3 3.4-3 7.5-3zM4.5 6.5v11c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3v-11M4.5 12c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3',
  stop: 'M7 7h10v10H7z',
  play: 'M8 5.5l11 6.5-11 6.5z',
  sparkle: 'M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9zM18.5 15.5l.8 2.2 2.2.8-2.2.8-.8 2.2-.8-2.2-2.2-.8 2.2-.8z',
  dumbbell: 'M3 10v4M6 7.5v9M9 9v6M9 12h6M15 9v6M18 7.5v9M21 10v4',
  barbell: 'M2 12h20M5.5 7.5v9M8.5 6v12M15.5 6v12M18.5 7.5v9',
  cable: 'M12 3v10M9 3h6M12 13a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5zM7 21h10',
  machine: 'M5 20V4h14v16M5 9h14M9 9v11M15 13h4M15 17h4',
  kettlebell: 'M9 7.5a3 3 0 0 1 6 0v1M7.4 8.5h9.2a2 2 0 0 1 1.9 2.5l-1.8 7.3a2 2 0 0 1-2 1.7H9.3a2 2 0 0 1-2-1.7L5.5 11a2 2 0 0 1 1.9-2.5z',
  band: 'M6 4c-3 5 3 11 0 16M18 4c3 5-3 11 0 16M6 12h12',
};

// Filled glyphs for the tab bar and a few emphasised spots.
const F = {
  tabSets: '<rect x="2.5" y="8.5" width="3" height="7" rx="1"/><rect x="6.5" y="5.5" width="3.5" height="13" rx="1.2"/><rect x="10" y="10.8" width="4" height="2.4"/><rect x="14" y="5.5" width="3.5" height="13" rx="1.2"/><rect x="18.5" y="8.5" width="3" height="7" rx="1"/>',
  tabSessions: '<path d="M12 5.2a8 8 0 1 1 0 16 8 8 0 0 1 0-16zm-1 3.8v5l4 2.2.9-1.4-3.2-1.9V9z"/><rect x="9.5" y="1.8" width="5" height="2.2" rx="1"/>',
  tabBody: '<circle cx="12" cy="4" r="2.3"/><path d="M3.8 7.8l7.3 1.6h1.8l7.3-1.6.5 1.9-5.8 1.7v4.1l2.3 6.6-2 .7-2.6-6.1h-.6l-2.6 6.1-2-.7 2.3-6.6v-4.1L3.3 9.7z"/>',
  tabToday: '<rect x="3.5" y="3.5" width="17" height="7.5" rx="2"/><rect x="3.5" y="13" width="17" height="7.5" rx="2"/>',
  trophy: '<path d="M7 3.5h10v6a5 5 0 0 1-10 0zM5 5h2v3.6A3 3 0 0 1 5 5zm14 0h-2v3.6A3 3 0 0 0 19 5zM11 14.3h2v3.2h2.5v3h-7v-3H11z"/>',
  dots: '<circle cx="5.5" cy="12" r="1.9"/><circle cx="12" cy="12" r="1.9"/><circle cx="18.5" cy="12" r="1.9"/>',
  bookFill: '<path d="M6.5 3h11a1 1 0 0 1 1 1v13.2H8A1.5 1.5 0 0 0 6.5 18.7zM6.5 18.7A1.5 1.5 0 0 0 8 20.2h10.5v1H8A2.5 2.5 0 0 1 5.5 18.7V4.5a1.5 1.5 0 0 1 1-1.4z"/>',
};

export function icon(name, cls = '') {
  if (F[name]) return raw(`<svg class="i ${cls}" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">${F[name]}</svg>`);
  const d = P[name] || P.info;
  return raw(`<svg class="i ${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${d}"/></svg>`);
}

export const EQUIP_ICON = { barbell: 'barbell', dumbbell: 'dumbbell', cable: 'cable', machine: 'machine', smith: 'machine', bodyweight: 'person', kettlebell: 'kettlebell', band: 'band', other: 'dumbbell' };
