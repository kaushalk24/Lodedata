'use strict';
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const api = async (url, opts) => {
  const r = await fetch(url, opts);
  if (!r.ok) throw new Error((await r.text()).slice(0, 300));
  return r.headers.get('content-type')?.includes('json') ? r.json() : r.text();
};
const status = m => { $('#status').textContent = m; if (m) setTimeout(() => {
  if ($('#status').textContent === m) $('#status').textContent = ''; }, 2500); };

const S = { design: null, results: null, selected: null, report: 'levels', libTab: 'cables' };

const TYPES = ['node', 'amplifier', 'tap', 'splitter', 'power_inserter',
               'power_supply', 'terminator', 'subscriber'];
// which library table supplies the part list for each element type
const PART_TABLE = { node: 'actives', amplifier: 'actives', tap: 'taps',
  splitter: 'passives', power_inserter: 'passives', power_supply: 'power_supplies' };

// ---------------------------------------------------------------- designs
async function loadDesignList(selectId) {
  const list = await api('/api/designs');
  const sel = $('#designPicker');
  sel.innerHTML = list.map(d => `<option value="${d.id}">${esc(d.name)}</option>`).join('');
  if (!list.length) return null;
  sel.value = selectId && list.some(d => d.id === selectId) ? selectId : list[0].id;
  return sel.value;
}
async function openDesign(id) {
  S.design = await api('/api/designs/' + id);
  S.selected = null;
  await refresh();
  renderParams();
  renderLibrary();
}
async function refresh() {
  S.results = await api(`/api/designs/${S.design.id}/results`);
  renderCascade();
  renderInspector();
  if ($('#tab-reports').classList.contains('active')) renderReport();
}
async function reloadDesign() {
  S.design = await api('/api/designs/' + S.design.id);
  await refresh();
}

// ---------------------------------------------------------------- cascade
const esc = s => String(s ?? '').replace(/[&<>"]/g, c =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const num = v => (v === '' || v === null || v === undefined) ? '' : v;

function partName(el) {
  const t = PART_TABLE[el.type];
  if (!t || !el.part_id) return '';
  return S.design.library[t]?.[el.part_id]?.name || '(missing)';
}

function renderCascade() {
  const tb = $('#cascade tbody');
  const r = S.results;
  if (!r || !r.order.length) {
    tb.innerHTML = `<tr><td colspan="17" class="empty">No devices yet. Add a node to start.</td></tr>`;
    $('#totals').textContent = '';
    return;
  }
  tb.innerHTML = r.order.map(id => {
    const row = r.rows[id], el = S.design.elements[id];
    const warn = row.warnings.length ? ' warn' : '';
    const sel = S.selected === id ? ' sel' : '';
    const pad = '&nbsp;'.repeat(row.depth * 4);
    return `<tr class="${warn}${sel}" data-id="${id}">
      <td>${pad}<span class="type-tag">${esc(row.type.replace('_', ' '))}</span>${esc(row.label)}</td>
      <td>${esc(partName(el))}</td>
      <td>${esc(row.cable_name)}</td>
      <td class="n">${row.length_ft || ''}</td>
      <td class="n">${row.cumulative_ft || ''}</td>
      <td class="n">${row.input.low}</td><td class="n">${row.input.high}</td>
      <td class="n">${row.output.low}</td><td class="n">${row.output.high}</td>
      <td class="n">${row.output.tilt}</td>
      <td class="n">${num(row.gain_high)}</td>
      <td class="n">${row.tap_port ? row.tap_port.high : ''}</td>
      <td class="n">${row.return_at_node ? row.return_at_node.high : ''}</td>
      <td class="n">${num(row.volts)}</td>
      <td class="n">${row.segment_current_a || ''}</td>
      <td class="n">${row.houses || ''}</td>
      <td class="note">${esc(row.warnings.join('; '))}</td></tr>`;
  }).join('');
  const t = r.totals;
  $('#totals').innerHTML = [
    ['Devices', t.elements], ['Amplifiers', t.amplifiers], ['Taps', t.taps],
    ['Homes passed', t.homes_passed], ['Footage', t.footage + ' ft'],
    ['Longest run', t.max_cumulative_ft + ' ft'],
    ['Tap ports', `${t.min_tap_port_dbmv} … ${t.max_tap_port_dbmv} dBmV`],
    ['Warnings', t.warnings],
  ].map(([k, v]) => `${k} <b>${esc(v)}</b>`).join(' · ')
    + (r.problems.length ? ` · <span class="note">${esc(r.problems.join('; '))}</span>` : '');
  $$('#cascade tbody tr[data-id]').forEach(tr =>
    tr.onclick = () => { S.selected = tr.dataset.id; renderCascade(); renderInspector(); });
}

// ---------------------------------------------------------------- inspector
function opts(table, selected, blank) {
  const entries = Object.values(S.design.library[table] || {})
    .sort((a, b) => a.name.localeCompare(b.name));
  return (blank ? `<option value="">— none —</option>` : '') + entries.map(p =>
    `<option value="${p.id}"${p.id === selected ? ' selected' : ''}>${esc(p.name)}</option>`).join('');
}
function field(label, html) {
  return `<div class="field"><label>${esc(label)}</label>${html}</div>`;
}
function input(name, value, type = 'text', step) {
  return `<input name="${name}" type="${type}" ${step ? `step="${step}"` : ''}
    value="${value === null || value === undefined ? '' : esc(value)}">`;
}

function renderInspector() {
  const box = $('#inspector');
  const el = S.selected && S.design.elements[S.selected];
  if (!el) { box.innerHTML = '<p class="empty">Select a device to edit it.</p>'; return; }
  const isSource = el.type === 'node' && !el.parent_id;
  const table = PART_TABLE[el.type];
  const parents = Object.values(S.design.elements).filter(e => e.id !== el.id);

  box.innerHTML = `<h2>${esc(el.label || el.type)}</h2>
    <form id="elForm">
      ${field('Label', input('label', el.label))}
      ${field('Type', `<select name="type">${TYPES.map(t =>
        `<option value="${t}"${t === el.type ? ' selected' : ''}>${t.replace('_', ' ')}</option>`).join('')}</select>`)}
      ${table ? field('Part', `<select name="part_id">${opts(table, el.part_id, true)}</select>`) : ''}
      ${field('Fed from', `<select name="parent_id"><option value="">— source —</option>${
        parents.map(p => `<option value="${p.id}"${p.id === el.parent_id ? ' selected' : ''}>${esc(p.label)}</option>`).join('')}</select>`)}
      ${field('Parent output port', input('parent_port', el.parent_port, 'number', '1'))}
      ${field('Cable', `<select name="cable_id">${opts('cables', el.cable_id, true)}</select>`)}
      ${field('Span length (ft)', input('length_ft', el.length_ft, 'number', '1'))}
      ${el.type === 'tap' || el.type === 'subscriber' ? field('Homes passed', input('houses', el.houses, 'number', '1')) : ''}
      ${el.type === 'amplifier' ? field('Output level at high freq (dBmV)', input('output_dbmv', el.output_dbmv, 'number', '0.1')) : ''}
      ${el.type === 'amplifier' ? field('Output tilt (dB)', input('tilt_db', el.tilt_db, 'number', '0.1')) : ''}
      ${isSource ? field('Launch level at high freq (dBmV)', input('source_dbmv', el.source_dbmv, 'number', '0.1')) : ''}
      ${isSource ? field('Launch tilt (dB)', input('source_tilt_db', el.source_tilt_db, 'number', '0.1')) : ''}
      ${el.type === 'power_supply' ? field('Supply volts', input('supply_volts', el.supply_volts, 'number', '1')) : ''}
      ${field('Notes', `<textarea name="notes" rows="2">${esc(el.notes || '')}</textarea>`)}
      <button type="submit">Save</button>
      <button type="button" id="delEl" class="danger">Delete (and everything below)</button>
    </form>`;

  $('#elForm').onsubmit = async ev => {
    ev.preventDefault();
    const fd = new FormData(ev.target);
    const body = { ...el };
    for (const [k, v] of fd.entries()) {
      if (['length_ft', 'output_dbmv', 'tilt_db', 'source_dbmv', 'source_tilt_db',
           'supply_volts'].includes(k)) body[k] = v === '' ? null : Number(v);
      else if (['parent_port', 'houses'].includes(k)) body[k] = Number(v || 0);
      else body[k] = v === '' ? null : v;
    }
    body.length_ft = body.length_ft ?? 0;
    delete body.id; delete body.x; delete body.y;
    await api(`/api/designs/${S.design.id}/elements/${el.id}`,
      { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    status('Saved'); await reloadDesign();
  };
  $('#delEl').onclick = async () => {
    if (!confirm('Delete this device and everything it feeds?')) return;
    await api(`/api/designs/${S.design.id}/elements/${el.id}`, { method: 'DELETE' });
    S.selected = null; status('Deleted'); await reloadDesign();
  };
}

// ---------------------------------------------------------------- add
async function addElement(type) {
  const parent = type === 'node' ? null : S.selected;
  if (type !== 'node' && !parent) { alert('Select the device this one is fed from first.'); return; }
  const defaults = { type, parent_id: parent, parent_port: 0, length_ft: 0 };
  if (type === 'node') { defaults.source_dbmv = 50; defaults.source_tilt_db = 10; }
  const el = await api(`/api/designs/${S.design.id}/elements`,
    { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(defaults) });
  S.selected = el.id;
  await reloadDesign();
}

// ---------------------------------------------------------------- reports
async function renderReport() {
  const rows = await api(`/api/designs/${S.design.id}/reports/${S.report}`);
  const thead = $('#reportTable thead'), tbody = $('#reportTable tbody');
  $('#csvLink').href = `/api/designs/${S.design.id}/reports/${S.report}?format=csv`;
  if (!rows.length) { thead.innerHTML = ''; tbody.innerHTML = '<tr><td class="empty">Nothing to report yet.</td></tr>'; return; }
  const cols = Object.keys(rows[0]);
  thead.innerHTML = `<tr>${cols.map(c => `<th>${esc(c.replace(/_/g, ' '))}</th>`).join('')}</tr>`;
  tbody.innerHTML = rows.map(r => `<tr>${cols.map(c =>
    `<td${typeof r[c] === 'number' ? ' class="n"' : ''}>${esc(r[c])}</td>`).join('')}</tr>`).join('');
}

// ---------------------------------------------------------------- library
function renderLibrary() {
  if (!S.design) return;
  const table = S.design.library[S.libTab] || {};
  const rows = Object.values(table).sort((a, b) => a.name.localeCompare(b.name));
  $('#libSource').textContent = `${S.design.library.name} — ${rows.length} parts`;
  const thead = $('#libTable thead'), tbody = $('#libTable tbody');
  if (!rows.length) { thead.innerHTML = ''; tbody.innerHTML = '<tr><td class="empty">Empty.</td></tr>'; return; }
  const cols = Object.keys(rows[0]).filter(c => c !== 'id');
  thead.innerHTML = `<tr>${cols.map(c => `<th>${esc(c.replace(/_/g, ' '))}</th>`).join('')}</tr>`;
  tbody.innerHTML = rows.map(p => `<tr>${cols.map(c => {
    const v = p[c];
    return `<td${typeof v === 'number' ? ' class="n"' : ''}>${esc(
      Array.isArray(v) ? JSON.stringify(v) : v)}</td>`;
  }).join('')}</tr>`).join('');
}

// ---------------------------------------------------------------- parameters
const PARAM_LABELS = {
  forward_low_mhz: 'Forward low frequency (MHz)', forward_high_mhz: 'Forward high frequency (MHz)',
  return_low_mhz: 'Return low frequency (MHz)', return_high_mhz: 'Return high frequency (MHz)',
  min_tap_port_dbmv: 'Minimum tap port level (dBmV)', max_tap_port_dbmv: 'Maximum tap port level (dBmV)',
  min_amp_input_dbmv: 'Minimum amplifier input (dBmV)',
  return_transmit_dbmv: 'Upstream transmit level (dBmV)',
  return_target_at_node_dbmv: 'Target return level at node (dBmV)',
  supply_volts: 'Default supply voltage (V)', min_device_volts: 'Minimum device voltage (V)',
  temperature_f: 'Design temperature (F)',
};
function renderParams() {
  if (!S.design) return;
  $('#paramForm').innerHTML = Object.entries(S.design.parameters).map(([k, v]) =>
    `<label for="p_${k}">${esc(PARAM_LABELS[k] || k)}</label>
     <input id="p_${k}" name="${k}" type="number" step="0.1" value="${esc(v)}">`).join('');
}
$('#saveParams').onclick = async () => {
  const fd = new FormData($('#paramForm'));
  const params = {};
  for (const [k, v] of fd.entries()) params[k] = Number(v);
  await api(`/api/designs/${S.design.id}`, { method: 'PATCH',
    headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ parameters: params }) });
  status('Parameters saved'); await reloadDesign();
};

// ---------------------------------------------------------------- import
$('#uploadSpec').onclick = async () => {
  const files = $('#specFiles').files;
  if (!files.length) { alert('Choose the spec files first.'); return; }
  const fd = new FormData();
  [...files].forEach(f => fd.append('files', f));
  status('Attaching…');
  try {
    const out = await api(`/api/designs/${S.design.id}/library/spec`, { method: 'POST', body: fd });
    $('#specResult').textContent =
      `Library: ${out.library.name}\n` +
      `Cables ${Object.keys(out.library.cables).length}, taps ${Object.keys(out.library.taps).length}, ` +
      `passives ${Object.keys(out.library.passives).length}, actives ${Object.keys(out.library.actives).length}\n` +
      `Re-matched ${out.relink.matched} part(s).\n` +
      (out.relink.unmatched.length
        ? `No match in the new spec set:\n  ${out.relink.unmatched.join('\n  ')}` : 'Everything matched.');
    status('Spec attached'); await reloadDesign(); renderLibrary();
  } catch (e) { $('#specResult').textContent = e.message; status('Failed'); }
};
$('#uploadNtw').onclick = async () => {
  const f = $('#ntwFile').files[0];
  if (!f) { alert('Choose a .ntw file first.'); return; }
  const fd = new FormData(); fd.append('file', f);
  status('Reading…');
  try {
    $('#ntwResult').textContent = JSON.stringify(await api('/api/import/ntw',
      { method: 'POST', body: fd }), null, 2);
    status('');
  } catch (e) { $('#ntwResult').textContent = e.message; status('Failed'); }
};

// ---------------------------------------------------------------- chrome
$$('.tab').forEach(b => b.onclick = () => {
  $$('.tab').forEach(x => x.classList.remove('active'));
  $$('.tab-panel').forEach(x => x.classList.remove('active'));
  b.classList.add('active');
  $('#tab-' + b.dataset.tab).classList.add('active');
  if (b.dataset.tab === 'reports') renderReport();
  if (b.dataset.tab === 'library') renderLibrary();
});
$$('.rep').forEach(b => b.onclick = () => {
  $$('.rep').forEach(x => x.classList.remove('active'));
  b.classList.add('active'); S.report = b.dataset.rep; renderReport();
});
$$('.lib').forEach(b => b.onclick = () => {
  $$('.lib').forEach(x => x.classList.remove('active'));
  b.classList.add('active'); S.libTab = b.dataset.lib; renderLibrary();
});
$$('[data-add]').forEach(b => b.onclick = () => addElement(b.dataset.add));
$('#designPicker').onchange = e => openDesign(e.target.value);
$('#newDesign').onclick = async () => {
  const name = prompt('Name for the new design?', 'New design');
  if (!name) return;
  const d = await api('/api/designs', { method: 'POST',
    headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name }) });
  await loadDesignList(d.id); await openDesign(d.id);
};

(async () => {
  let id = await loadDesignList();
  if (!id) {
    const d = await api('/api/designs', { method: 'POST',
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: 'First design' }) });
    id = await loadDesignList(d.id);
  }
  await openDesign(id);
})();
