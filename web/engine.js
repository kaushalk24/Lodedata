/* HFC design engine: pure calculation, no DOM.
 * Math and selection rules follow docs/02-hfc-engineering-core.md.
 * Levels in dBmV, losses in dB, lengths in feet (loss specs are per 100 ft). */

const Engine = (() => {
  const FWD = ['hi', 'lo'];
  const RET = ['rh', 'rl'];
  const SUFFIX = { hi: 'Hi', lo: 'Lo', rh: 'Rh', rl: 'Rl' };
  const BRACKETS = { '(': [')', 2], '[': [']', 4], '{': ['}', 8] };
  const OPEN = { 2: '(', 4: '[', 8: '{' };
  const CLOSE = { 2: ')', 4: ']', 8: '}' };
  const NONE = { hi: -Infinity, lo: -Infinity };
  const EPS = 1e-9;

  const num = (v, d = 0) => (v === '' || v == null || isNaN(Number(v)) ? d : Number(v));
  const yes = v => v === true || v === 'true' || v === 'Y' || v === 'y' || v === 1 || v === '1';
  const leg = (spec, name, f) => num(spec[name + SUFFIX[f]]);
  const err = (node, sev, field, msg) => ({ node, sev, field, msg });
  const fmt = v => (isFinite(v) ? v.toFixed(1) : '—');

  // ---------- equipment notation ----------
  // 11 = active ID · [26] 4-port tap · (26) 2-port · {26} 8-port · [*] auto tap
  // 8[3] coupler ID 8 feeding branch 3 · -8[3] reversed legs · *[3] auto coupler · PS
  function parseEquip(text) {
    const out = { active: null, taps: [], couplers: [], ps: false, errors: [] };
    for (const tok of String(text || '').trim().split(/\s+/).filter(Boolean)) {
      let m;
      if (/^PS$/i.test(tok)) { out.ps = true; continue; }
      if ((m = /^(-?)(\*|[A-Za-z0-9.]+)\[(\d+)\]$/.exec(tok))) {
        out.couplers.push({ id: m[2] === '*' ? null : m[2], branch: m[3], neg: m[1] === '-' });
        continue;
      }
      const b = BRACKETS[tok[0]];
      if (b && tok[tok.length - 1] === b[0]) {
        const v = tok.slice(1, -1);
        if (v === '*' || /^\d+(\.\d+)?$/.test(v)) {
          out.taps.push({ ports: b[1], value: v === '*' ? null : Number(v) });
          continue;
        }
      }
      if (/^[A-Za-z0-9]+$/.test(tok)) {
        if (out.active) out.errors.push(`Only one active per node ("${tok}")`);
        else out.active = tok;
        continue;
      }
      out.errors.push(`Cannot read "${tok}"`);
    }
    if (out.taps.length > 4) out.errors.push('More than 4 taps at one node');
    if (out.couplers.length > 2) out.errors.push('More than 2 couplers at one node');
    return out;
  }

  function formatEquip(eq) {
    const t = [];
    if (eq.active) t.push(eq.active);
    for (const x of eq.taps) t.push(OPEN[x.ports] + (x.value == null ? '*' : x.value) + CLOSE[x.ports]);
    for (const c of eq.couplers) t.push(`${c.neg ? '-' : ''}${c.id == null ? '*' : c.id}[${c.branch}]`);
    if (eq.ps) t.push('PS');
    return t.join(' ');
  }

  // ---------- specs ----------
  function indexSpecs(specs) {
    const P = specs.parameters;
    return {
      P,
      cables: new Map(specs.cables.map(c => [String(c.id), c])),
      actives: new Map(specs.actives.map(a => [String(a.id), a])),
      couplers: new Map(specs.couplers.map(c => [String(c.id), c])),
      taps: specs.taps,
      eqValues: String(P.eqValues).split(/[\s,]+/).filter(Boolean).map(Number).sort((a, b) => a - b),
    };
  }
  const tsgOf = (row, P) => num(row.tsg) || num(P.defaultTsg, 1);
  const tapCandidates = (S, tsg, ports) =>
    S.taps.filter(t => num(t.tsg) === tsg && num(t.ports) === ports).sort((a, b) => num(b.value) - num(a.value));
  const findTap = (S, tsg, ports, value) =>
    S.taps.find(t => num(t.tsg) === tsg && num(t.ports) === ports && num(t.value) === value) ||
    S.taps.find(t => num(t.ports) === ports && num(t.value) === value);
  const legsOf = neg => (neg ? { down: 'tap', branch: 'thru' } : { down: 'thru', branch: 'tap' });

  function spanLoss(S, row) {
    const cab = S.cables.get(String(row.cbl));
    const ft = num(row.ft);
    const loss = {};
    for (const f of [...FWD, ...RET]) loss[f] = cab ? num(cab[f]) * ft / 100 : 0;
    return { cab, ft, loss };
  }

  // Device order inside a node (Lode): active -> taps -> couplers.
  function devicesOf(eq) {
    const d = [];
    if (eq.active) d.push({ kind: 'active' });
    eq.taps.forEach((_, i) => d.push({ kind: 'tap', i }));
    eq.couplers.forEach((_, i) => d.push({ kind: 'coupler', i }));
    return d;
  }

  // ---------- topology ----------
  function buildTree(net) {
    const branches = net.branches || {};
    const keys = Object.keys(branches).sort((a, b) => num(a) - num(b));
    const byBranch = {};
    const errors = [];
    for (const b of keys) {
      byBranch[b] = branches[b].map((row, i) => ({ id: `${b}.${i + 1}`, b, i, row, eq: parseEquip(row.eq) }));
    }
    const feeds = {};
    for (const b of keys) {
      for (const n of byBranch[b]) {
        n.eq.couplers.forEach((c, k) => {
          if (c.branch === '1') errors.push(err(n.id, 'red', 'coupler', 'Branch 1 is the start of the network and cannot be fed'));
          else if (!byBranch[c.branch]) errors.push(err(n.id, 'red', 'coupler', `Branch ${c.branch} does not exist`));
          else if (feeds[c.branch]) errors.push(err(n.id, 'red', 'coupler', `Branch ${c.branch} is already fed from node ${feeds[c.branch].node.id}`));
          else feeds[c.branch] = { node: n, k };
        });
      }
    }
    return { keys, byBranch, feeds, errors };
  }
  const feedsBranch = (T, n, k, b) => T.feeds[b] && T.feeds[b].node === n && T.feeds[b].k === k;

  // ---------- pass 1: bottom-up required input (docs/02 §3.2) ----------
  function passReq(T, S) {
    const P = S.P;
    const minTap = { hi: num(P.minTapHi), lo: num(P.minTapLo) };
    const req = new Map();
    const needAt = new Map();
    const done = new Set();

    const branchReq = b => {
      const list = T.byBranch[b];
      if (!list || !list.length) return NONE;
      if (!done.has(b)) { done.add(b); walk(b); }
      return req.get(list[0].id) || NONE;
    };

    const walk = b => {
      let next = NONE;
      const list = T.byBranch[b];
      for (let i = list.length - 1; i >= 0; i--) {
        const n = list[i];
        const devs = devicesOf(n.eq);
        const needs = new Array(devs.length + 1);
        let need = next;
        needs[devs.length] = need;
        for (let d = devs.length - 1; d >= 0; d--) {
          const dev = devs[d];
          if (dev.kind === 'coupler') {
            const c = n.eq.couplers[dev.i];
            const child = feedsBranch(T, n, dev.i, c.branch) ? branchReq(c.branch) : NONE;
            const L = legsOf(c.neg);
            const cands = c.id == null ? [...S.couplers.values()] : [S.couplers.get(c.id)].filter(Boolean);
            need = minVec(cands.map(k => maxVec(k, L.down, need, L.branch, child))) || need;
          } else if (dev.kind === 'tap') {
            const t = n.eq.taps[dev.i];
            const tsg = tsgOf(n.row, P);
            const auto = t.value == null;
            const cands = auto ? tapCandidates(S, tsg, t.ports) : [findTap(S, tsg, t.ports, t.value)].filter(Boolean);
            const vecs = cands
              .filter(s => !(auto && yes(s.term) && need.hi > -Infinity))
              .map(s => {
                const v = {};
                for (const f of FWD) v[f] = Math.max(minTap[f] + leg(s, 'tap', f), yes(s.term) ? -Infinity : leg(s, 'thru', f) + need[f]);
                return v;
              });
            need = minVec(vecs) || need;
          } else {
            const a = S.actives.get(n.eq.active);
            need = a ? { hi: num(a.minIn) + num(a.reserve), lo: -Infinity } : NONE;
          }
          needs[d] = need;
        }
        needAt.set(n.id, needs);
        const { loss } = spanLoss(S, n.row);
        const r = { hi: need.hi + loss.hi, lo: need.lo + loss.lo };
        req.set(n.id, r);
        next = r;
      }
    };

    for (const b of T.keys) branchReq(b);
    return { req, needAt };
  }
  function maxVec(k, downLeg, down, branchLeg, branch) {
    const v = {};
    for (const f of FWD) v[f] = Math.max(leg(k, downLeg, f) + down[f], leg(k, branchLeg, f) + branch[f]);
    return v;
  }
  function minVec(vecs) {
    let best = null;
    for (const v of vecs) if (!best || v.hi < best.hi || (v.hi === best.hi && v.lo < best.lo)) best = v;
    return best;
  }

  // ---------- actives: output-referenced, pad/EQ selection (docs/02 §4) ----------
  function runActive(a, L, S) {
    const P = S.P;
    const eNeed = (num(a.outHi) - num(a.outLo)) - (num(a.gainHi) - num(a.gainLo)) - (L.hi - L.lo);
    let eq = 0;
    if (yes(P.allowOverEq)) {
      for (const v of S.eqValues) if (Math.abs(v - eNeed) < Math.abs(eq - eNeed)) eq = v;
    } else {
      for (const v of S.eqValues) if (v <= eNeed + EPS && v > eq) eq = v;
    }
    const eqHi = eq > 0 ? num(P.eqLoss) : 0;
    const eqLo = eqHi + eq;
    const padNeed = L.hi + num(a.gainHi) - eqHi - num(a.outHi);
    const step = num(P.padStep, 1) || 1;
    const pad = Math.max(0, Math.min(num(P.padMax, 20), Math.floor(padNeed / step + EPS) * step));
    const out = { hi: L.hi - pad - eqHi + num(a.gainHi), lo: L.lo - pad - eqLo + num(a.gainLo) };
    return { eq, eNeed, pad, padNeed, out };
  }

  // ---------- taps: highest value that meets every limit (docs/02 §3.3) ----------
  function selectTap(cands, L, ret, isLast, lim) {
    const usable = cands.filter(t => isLast || !yes(t.term));
    const fwd = t => L.hi - leg(t, 'tap', 'hi') >= lim.min.hi - EPS && L.lo - leg(t, 'tap', 'lo') >= lim.min.lo - EPS;
    const win = t => L.hi - leg(t, 'tap', 'hi') <= lim.max + EPS;
    const rtn = t => RET.every(r => lim.rai[r] + ret[r] + leg(t, 'tap', r) <= lim.maxRet[r] + EPS);
    return usable.find(t => fwd(t) && win(t) && rtn(t)) ||
      usable.find(t => fwd(t) && rtn(t)) ||
      usable.find(fwd) ||
      usable[usable.length - 1] || null;
  }

  // ---------- pass 2: top-down levels, selections, return, perf ----------
  function passLevels(T, S, net, req, needAt, out) {
    const P = S.P;
    const lim = {
      min: { hi: num(P.minTapHi), lo: num(P.minTapLo) },
      max: num(P.minTapHi) + num(P.tapWindow),
      rai: { rh: num(P.retInRh), rl: num(P.retInRl) },
      maxRet: { rh: num(P.maxRetRh), rl: num(P.maxRetRl) },
    };
    const E = out.errors;
    const visited = new Set();

    const walk = (b, st) => {
      visited.add(b);
      let L = { ...st.L };
      let ret = { ...st.ret };
      let perf = st.perf;
      let chain = st.chain;
      let parent = st.parent;
      const list = T.byBranch[b];
      list.forEach((n, idx) => {
        const R = {
          id: n.id, b, i: n.i, row: n.row, eq: n.eq, parent, errors: [],
          active: null, taps: [], couplers: [], perf: null, tapMin: null, retMax: null,
        };
        out.nodes.set(n.id, R);
        out.order.push(n.id);
        for (const m of n.eq.errors) E.push(err(n.id, 'red', 'equip', m));

        const { cab, ft, loss } = spanLoss(S, n.row);
        if (!cab && (ft > 0 || String(n.row.cbl || '').trim())) E.push(err(n.id, 'red', 'cable', `Cable "${n.row.cbl}" is not in the cable specs`));
        R.span = loss;
        L = { hi: L.hi - loss.hi, lo: L.lo - loss.lo };
        ret = { rh: ret.rh + loss.rh, rl: ret.rl + loss.rl };
        R.in = { ...L };
        R.retIn = { ...ret };

        const devs = devicesOf(n.eq);
        const needs = needAt.get(n.id);
        const hasNext = idx < list.length - 1;

        devs.forEach((dev, d) => {
          if (dev.kind === 'active') {
            const a = S.actives.get(n.eq.active);
            if (!a) { E.push(err(n.id, 'red', 'active', `Active ID "${n.eq.active}" is not in the active specs`)); return; }
            const r = runActive(a, L, S);
            const minIn = num(a.minIn);
            if (L.hi < minIn - EPS) E.push(err(n.id, 'red', 'active', `Active input ${fmt(L.hi)} is below minimum ${fmt(minIn)}`));
            else if (L.hi < minIn + num(a.reserve) - EPS) E.push(err(n.id, 'yellow', 'active', `Active input ${fmt(L.hi)} is within reserve gain (${fmt(minIn)}–${fmt(minIn + num(a.reserve))})`));
            if (r.padNeed < -0.05) E.push(err(n.id, 'red', 'active', `Not enough gain: output ${fmt(r.out.hi)} is below design ${fmt(num(a.outHi))}`));
            if (r.padNeed > num(P.padMax, 20) + 0.05) E.push(err(n.id, 'yellow', 'active', `Input too hot: needs ${fmt(r.padNeed)} dB of pad, largest is ${fmt(num(P.padMax))}`));
            const x = {
              cn: 59 + L.hi - num(a.nf),
              ctb: num(a.ctb) - num(P.ctbDerate) * (r.out.hi - num(a.refOut)),
              cso: num(a.cso) - num(P.csoDerate) * (r.out.hi - num(a.refOut)),
            };
            R.active = { id: String(a.id), spec: a, in: { ...L }, ...r, contrib: x, leBefore: 0, leAfter: 0 };
            perf = [...perf, x];
            if (String(a.type).toUpperCase() === 'LE') {
              chain.forEach((prev, j) => { prev.active.leAfter = Math.max(prev.active.leAfter, chain.length - j); });
              R.active.leBefore = chain.length;
              chain = [...chain, R];
            } else {
              chain = [];
            }
            L = { ...r.out };
            ret = { rh: 0, rl: 0 };
          } else if (dev.kind === 'tap') {
            const t = n.eq.taps[dev.i];
            const tsg = tsgOf(n.row, P);
            const isLast = dev.i === n.eq.taps.length - 1 && !n.eq.couplers.length && !hasNext;
            const auto = t.value == null;
            const s = auto ? selectTap(tapCandidates(S, tsg, t.ports), L, ret, isLast, lim) : findTap(S, tsg, t.ports, t.value);
            if (!s) { E.push(err(n.id, 'red', 'equip', `No ${t.ports}-port tap${auto ? '' : ' of value ' + t.value} in TSG ${tsg}`)); return; }
            const port = { hi: L.hi - leg(s, 'tap', 'hi'), lo: L.lo - leg(s, 'tap', 'lo') };
            const retReq = { rh: lim.rai.rh + ret.rh + leg(s, 'tap', 'rh'), rl: lim.rai.rl + ret.rl + leg(s, 'tap', 'rl') };
            const label = OPEN[t.ports] + num(s.value) + CLOSE[t.ports];
            if (port.hi < lim.min.hi - EPS || port.lo < lim.min.lo - EPS)
              E.push(err(n.id, 'red', 'tap', `Tap ${label} output ${fmt(port.hi)}/${fmt(port.lo)} is below minimum ${fmt(lim.min.hi)}/${fmt(lim.min.lo)}`));
            else if (port.hi > lim.max + EPS)
              E.push(err(n.id, 'red', 'tap', `Tap ${label} output ${fmt(port.hi)} is above maximum ${fmt(lim.max)} (tap window)`));
            for (const r of RET) {
              if (retReq[r] > lim.maxRet[r] + EPS) E.push(err(n.id, 'red', 'ret', `Tap ${label} needs return level ${fmt(retReq[r])} at ${r.toUpperCase()}, above maximum ${fmt(lim.maxRet[r])}`));
            }
            if (yes(s.term) && !isLast) E.push(err(n.id, 'red', 'equip', `Terminating tap ${label} is not at the end of the line`));
            R.taps.push({ value: num(s.value), ports: t.ports, part: s.part, auto, port, retReq, spec: s, in: { ...L } });
            L = { hi: L.hi - leg(s, 'thru', 'hi'), lo: L.lo - leg(s, 'thru', 'lo') };
            ret = { rh: ret.rh + leg(s, 'thru', 'rh'), rl: ret.rl + leg(s, 'thru', 'rl') };
          } else {
            const c = n.eq.couplers[dev.i];
            const fed = feedsBranch(T, n, dev.i, c.branch);
            const childList = T.byBranch[c.branch];
            const child = fed && childList && childList.length ? req.get(childList[0].id) || NONE : NONE;
            const down = needs[d + 1];
            const lg = legsOf(c.neg);
            const auto = c.id == null;
            let s;
            if (auto) {
              // Both legs fed → lowest thru loss. Otherwise feed the branch first (Lode reports
              // "cannot select coupler" only when the branch cannot be fed); a short thru side
              // shows up as errors at the downstream nodes where the level runs out.
              const all = [...S.couplers.values()];
              const reachesDown = k => FWD.every(f => L[f] - leg(k, lg.down, f) >= down[f] - EPS);
              const reachesBranch = k => FWD.every(f => L[f] - leg(k, lg.branch, f) >= child[f] - EPS);
              const byDown = (x, y) => leg(x, lg.down, 'hi') - leg(y, lg.down, 'hi');
              s = all.filter(k => reachesDown(k) && reachesBranch(k)).sort(byDown)[0] || all.filter(reachesBranch).sort(byDown)[0];
              if (!s) {
                const margin = k => Math.min(...FWD.map(f => L[f] - leg(k, lg.branch, f) - child[f]));
                s = all.slice().sort((x, y) => margin(y) - margin(x))[0];
                E.push(err(n.id, 'red', 'coupler', `Cannot select coupler at node ${n.id}: not enough signal to feed branch ${c.branch}`));
              }
            } else {
              s = S.couplers.get(c.id);
            }
            if (!s) { E.push(err(n.id, 'red', 'coupler', `Coupler ID "${c.id}" is not in the coupler specs`)); return; }
            const bL = { hi: L.hi - leg(s, lg.branch, 'hi'), lo: L.lo - leg(s, lg.branch, 'lo') };
            const bRet = { rh: ret.rh + leg(s, lg.branch, 'rh'), rl: ret.rl + leg(s, lg.branch, 'rl') };
            R.couplers.push({ id: String(s.id), part: s.part, auto, branch: c.branch, neg: c.neg, branchIn: bL });
            L = { hi: L.hi - leg(s, lg.down, 'hi'), lo: L.lo - leg(s, lg.down, 'lo') };
            ret = { rh: ret.rh + leg(s, lg.down, 'rh'), rl: ret.rl + leg(s, lg.down, 'rl') };
            if (fed && childList && childList.length) walk(c.branch, { L: bL, ret: bRet, perf, chain, parent: n.id });
          }
        });

        R.perf = {
          cn: combine([num(P.startCN), ...perf.map(x => x.cn)], num(P.cnAdd, 10)),
          ctb: combine([num(P.startCTB), ...perf.map(x => x.ctb)], num(P.ctbAdd, 20)),
          cso: combine([num(P.startCSO), ...perf.map(x => x.cso)], num(P.csoAdd, 15)),
        };
        if (R.taps.length) {
          R.tapMin = { hi: Math.min(...R.taps.map(t => t.port.hi)), lo: Math.min(...R.taps.map(t => t.port.lo)) };
          R.retMax = { rh: Math.max(...R.taps.map(t => t.retReq.rh)), rl: Math.max(...R.taps.map(t => t.retReq.rl)) };
          const p = R.perf;
          if (p.cn < num(P.minCN) - EPS) E.push(err(n.id, 'red', 'perf', `C/N ${fmt(p.cn)} is below minimum ${fmt(num(P.minCN))}`));
          if (p.ctb < num(P.minCTB) - EPS) E.push(err(n.id, 'red', 'perf', `CTB ${fmt(p.ctb)} is below minimum ${fmt(num(P.minCTB))}`));
          if (p.cso < num(P.minCSO) - EPS) E.push(err(n.id, 'red', 'perf', `CSO ${fmt(p.cso)} is below minimum ${fmt(num(P.minCSO))}`));
        }
        R.out = { ...L };
        parent = n.id;
      });
    };

    const start = { hi: num(net.start && net.start.hi), lo: num(net.start && net.start.lo) };
    if (T.byBranch['1']) walk('1', { L: start, ret: { rh: 0, rl: 0 }, perf: [], chain: [], parent: null });
    else E.push(err('1.1', 'red', 'equip', 'The network has no branch 1'));
    for (const b of T.keys) {
      if (!visited.has(b) && T.byBranch[b].length) E.push(err(`${b}.1`, 'yellow', 'coupler', `Branch ${b} is not fed by any coupler and is not calculated`));
    }
  }
  function combine(values, k) {
    let s = 0;
    for (const v of values) s += Math.pow(10, -v / k);
    return -k * Math.log10(s);
  }

  // ---------- LE cascade rules (IDs 11 / 21 22 / 31 32 33) ----------
  function checkCascade(out, S) {
    const max = num(S.P.maxLeCascade, 3);
    for (const R of out.nodes.values()) {
      const a = R.active;
      if (!a || String(a.spec.type).toUpperCase() !== 'LE') continue;
      const code = String(a.spec.cascade || '');
      const total = num(code[0]), pos = num(code[1]);
      const N = a.leBefore, M = a.leAfter;
      if (!total || !pos) continue;
      if (total > max || N + 1 + M > max || pos !== N + 1 || N + 1 + M > total)
        out.errors.push(err(R.id, 'red', 'cascade', `LE ${a.id} is out of cascade: ${N} before, ${M} after (max LE cascade ${max})`));
    }
  }

  // ---------- powering (docs/02 §7) ----------
  const parseVI = s => String(s || '').split(/[\s,]+/).filter(Boolean)
    .map(p => p.split(':').map(Number)).filter(p => p.length === 2 && p.every(isFinite)).sort((x, y) => x[0] - y[0]);
  function ampsAt(vi, V) {
    if (!vi.length) return 0;
    let a = vi[0][1];
    for (const [v, amps] of vi) if (V >= v) a = amps;
    return a;
  }

  function passPower(out, S, onlyPs) {
    const P = S.P;
    const nodes = [...out.nodes.values()];
    const adj = new Map(nodes.map(R => [R.id, []]));
    for (const R of nodes) {
      if (!R.parent || !adj.has(R.parent)) continue;
      const cab = S.cables.get(String(R.row.cbl));
      const ohm = (cab ? num(cab.loop) : 0) * num(R.row.ft) / 1000;
      const unpowered = cab && num(cab.loop) >= 99;
      adj.get(R.id).push({ to: R.parent, ohm, unpowered, span: R.id });
      adj.get(R.parent).push({ to: R.id, ohm, unpowered, span: R.id });
    }
    const ps = onlyPs ? [onlyPs] : nodes.filter(R => R.eq.ps).map(R => R.id);
    if (!ps.length) return null;

    // Each node is powered by the nearest supply (a power block sits between supplies).
    const owner = new Map(), zp = new Map(), order = [];
    const queue = [...ps];
    ps.forEach(id => owner.set(id, id));
    while (queue.length) {
      const id = queue.shift();
      order.push(id);
      for (const e of adj.get(id)) {
        if (owner.has(e.to)) continue;
        owner.set(e.to, owner.get(id));
        zp.set(e.to, { id, ohm: e.ohm, unpowered: e.unpowered, span: e.span });
        queue.push(e.to);
      }
    }
    const vi = new Map(nodes.map(R => [R.id, R.active ? parseVI(R.active.spec.vi) : []]));
    const Vps = num(P.psVolts, 90);
    let V = new Map(order.map(id => [id, Vps]));
    let load = new Map(), sub = new Map();
    for (let it = 0; it < 80; it++) {
      load = new Map(order.map(id => [id, ampsAt(vi.get(id), V.get(id))]));
      sub = new Map();
      for (let k = order.length - 1; k >= 0; k--) {
        const id = order[k];
        const s = (sub.get(id) || 0) + load.get(id);
        sub.set(id, s);
        const p = zp.get(id);
        if (p) sub.set(p.id, (sub.get(p.id) || 0) + s);
      }
      const nv = new Map();
      let delta = 0;
      for (const id of order) {
        const p = zp.get(id);
        const v = p ? nv.get(p.id) - sub.get(id) * p.ohm : Vps;
        nv.set(id, v);
        delta = Math.max(delta, Math.abs(v - V.get(id)));
      }
      V = it > 20 ? new Map(order.map(id => [id, (V.get(id) + nv.get(id)) / 2])) : nv;
      if (delta < 1e-3) break;
    }

    const result = { nodes: new Map(), supplies: [], errors: [] };
    const E = result.errors;
    for (const id of order) {
      const R = out.nodes.get(id);
      const thru = sub.get(id) - load.get(id);
      const p = zp.get(id);
      result.nodes.set(id, { volts: V.get(id), load: load.get(id), thru, ps: owner.get(id) });
      const v = vi.get(id);
      if (v.length && V.get(id) < v[0][0] - EPS) E.push(err(id, 'red', 'power', `Voltage ${fmt(V.get(id))} V is below the active's minimum ${fmt(v[0][0])} V`));
      const ratings = [...R.taps.map(t => t.spec.maxAmps), ...R.couplers.map(c => (S.couplers.get(c.id) || {}).maxAmps)];
      if (R.active) ratings.push(R.active.spec.maxAmps);
      const rating = Math.min(...ratings.map(x => num(x, Infinity)));
      if (thru > rating + EPS) E.push(err(id, 'red', 'power', `${fmt(thru)} A passes through equipment rated ${fmt(rating)} A`));
      if (p && p.unpowered && sub.get(id) > EPS) E.push(err(p.span, 'red', 'power', 'Power passes through a cable marked not for powering (loop 99)'));
    }
    for (const id of ps) {
      const amps = sub.get(id) || 0;
      const zone = order.filter(n => owner.get(n) === id);
      const vmin = Math.min(...zone.map(n => V.get(n)));
      result.supplies.push({ node: id, amps, volts: Vps, actives: zone.filter(n => out.nodes.get(n).active).length, vmin, vminAt: zone.find(n => V.get(n) === vmin) });
      if (amps > num(P.psMaxAmps, 15) + EPS) E.push(err(id, 'red', 'power', `Power supply load ${fmt(amps)} A exceeds ${fmt(num(P.psMaxAmps))} A`));
    }
    return result;
  }

  // ---------- main entry ----------
  function calc(net, specs, opts = {}) {
    const S = indexSpecs(specs);
    const T = buildTree(net);
    const out = { nodes: new Map(), order: [], errors: [...T.errors], power: null };
    const { req, needAt } = passReq(T, S);
    passLevels(T, S, net, req, needAt, out);
    checkCascade(out, S);
    if (!opts.noPower) {
      out.power = passPower(out, S);
      if (out.power) out.errors.push(...out.power.errors);
    }
    for (const e of out.errors) {
      const R = out.nodes.get(e.node);
      if (R) R.errors.push(e);
    }
    return out;
  }

  // Power supply placement: try every node, keep the best by objective (docs/02 §7.3).
  function optimizePS(net, specs, objective) {
    const S = indexSpecs(specs);
    const base = calc(net, specs, { noPower: true });
    const Vps = num(S.P.psVolts, 90);
    let best = null;
    for (const id of base.order) {
      const pw = passPower(base, S, id);
      if (!pw) continue;
      const loaded = [...pw.nodes.entries()].filter(([n]) => base.nodes.get(n).active);
      const volts = (loaded.length ? loaded : [...pw.nodes.entries()]).map(([, x]) => x.volts);
      const low = Math.min(...volts);
      let score;
      if (objective === 'sqdrop') score = -volts.reduce((s, v) => s + (Vps - v) ** 2, 0);
      else if (objective === 'balanced') {
        const dirs = [...pw.nodes.entries()].filter(([n]) => n !== id && isChildOf(base, n, id)).map(([n, x]) => x.load + x.thru).filter(a => a > EPS);
        if (dirs.length < 2) continue;
        score = -(Math.max(...dirs) - Math.min(...dirs)) + low * 1e-6;
      } else score = low;
      if (!best || score > best.score) best = { node: id, score, low };
    }
    return best;
  }
  // true when n is directly connected to ps (one span away)
  function isChildOf(base, n, ps) {
    const R = base.nodes.get(n);
    return R.parent === ps || base.nodes.get(ps).parent === n;
  }

  // Write auto-selected taps and couplers into the equipment text (fixes them).
  function lockSelections(net, result) {
    for (const [b, rows] of Object.entries(net.branches)) {
      rows.forEach((row, i) => {
        const R = result.nodes.get(`${b}.${i + 1}`);
        if (!R || (!R.taps.some(t => t.auto) && !R.couplers.some(c => c.auto))) return;
        const eq = parseEquip(row.eq);
        R.taps.forEach((t, k) => { if (eq.taps[k]) eq.taps[k].value = t.value; });
        R.couplers.forEach((c, k) => { if (eq.couplers[k]) eq.couplers[k].id = c.id; });
        row.eq = formatEquip(eq);
      });
    }
  }
  function unlockTaps(net) {
    for (const rows of Object.values(net.branches)) {
      for (const row of rows) {
        row.eq = String(row.eq || '').split(/\s+/).filter(Boolean)
          .map(tok => (BRACKETS[tok[0]] && tok[tok.length - 1] === BRACKETS[tok[0]][0] ? tok[0] + '*' + tok[tok.length - 1] : tok))
          .join(' ');
      }
    }
  }

  // ---------- reports ----------
  const r1 = v => (isFinite(v) ? Math.round(v * 10) / 10 : '');
  function countBy(items) {
    const m = new Map();
    for (const k of items) m.set(k, (m.get(k) || 0) + 1);
    return [...m.entries()].sort((a, b) => String(a[0]).localeCompare(String(b[0]), undefined, { numeric: true }));
  }

  function reports(result, specs, net) {
    const S = indexSpecs(specs);
    const nodes = result.order.map(id => result.nodes.get(id));
    const pw = result.power;

    const bomRows = [];
    const feet = new Map();
    let homes = 0, total = 0;
    for (const R of nodes) {
      const ft = num(R.row.ft);
      total += ft;
      homes += num(R.row.hc);
      if (ft) feet.set(String(R.row.cbl), (feet.get(String(R.row.cbl)) || 0) + ft);
    }
    for (const [id, ft] of [...feet.entries()].sort()) {
      const c = S.cables.get(id);
      bomRows.push(['Cable', `${id} ${c ? c.name : '?'}`, ft, 'ft', (ft / 5280).toFixed(2) + ' mi']);
    }
    for (const [k, q] of countBy(nodes.filter(R => R.active).map(R => `${R.active.spec.part} (${R.active.id})`))) bomRows.push(['Active', k, q, 'ea', '']);
    for (const [k, q] of countBy(nodes.flatMap(R => R.taps.map(t => t.part)))) bomRows.push(['Tap', k, q, 'ea', '']);
    for (const [k, q] of countBy(nodes.flatMap(R => R.couplers.map(c => c.part)))) bomRows.push(['Coupler', k, q, 'ea', '']);
    for (const [k, q] of countBy(nodes.filter(R => R.active && R.active.pad > 0).map(R => `PAD ${R.active.pad} dB`))) bomRows.push(['Plug-in', k, q, 'ea', '']);
    for (const [k, q] of countBy(nodes.filter(R => R.active && R.active.eq > 0).map(R => `EQ ${R.active.eq} dB`))) bomRows.push(['Plug-in', k, q, 'ea', '']);
    const psCount = nodes.filter(R => R.eq.ps).length;
    if (psCount) bomRows.push(['Power', 'Power supply', psCount, 'ea', '']);
    bomRows.push(['Total', 'Plant footage', total, 'ft', (total / 5280).toFixed(2) + ' mi']);
    bomRows.push(['Total', 'Homes passed', homes, 'hh', total ? r1(homes / (total / 5280)) + ' per mi' : '']);

    return {
      bom: { title: 'Bill of Materials', cols: ['Section', 'Item', 'Qty', 'Unit', 'Note'], rows: bomRows },
      active: {
        title: 'Active Report',
        cols: ['Node', 'ID', 'Name', 'Part', 'In Hi', 'In Lo', 'Pad', 'EQ', 'Out Hi', 'Out Lo', 'LE before', 'LE after', 'Volts'],
        rows: nodes.filter(R => R.active).map(R => {
          const a = R.active;
          const p = pw && pw.nodes.get(R.id);
          return [R.id, a.id, a.spec.name, a.spec.part, r1(a.in.hi), r1(a.in.lo), a.pad, a.eq, r1(a.out.hi), r1(a.out.lo),
            a.leBefore, a.leAfter, p ? r1(p.volts) : ''];
        }),
      },
      tap: {
        title: 'Network Tap Report',
        cols: ['Node', 'Tap', 'Part', 'HC', 'In Hi', 'Port Hi', 'Port Lo', 'Fwd Tilt', 'Ret Rh', 'Ret Rl', 'Ret Tilt'],
        rows: nodes.flatMap(R => R.taps.map(t => [R.id, OPEN[t.ports] + t.value + CLOSE[t.ports], t.part, num(R.row.hc),
          r1(t.in.hi), r1(t.port.hi), r1(t.port.lo), r1(t.port.hi - t.port.lo), r1(t.retReq.rh), r1(t.retReq.rl), r1(t.retReq.rh - t.retReq.rl)])),
      },
      perf: {
        title: 'Performance Distribution',
        cols: ['Node', 'Taps', 'C/N', 'CTB', 'CSO'],
        rows: nodes.filter(R => R.taps.length).map(R => [R.id, R.taps.length, r1(R.perf.cn), r1(R.perf.ctb), r1(R.perf.cso)]),
      },
      power: {
        title: 'Power Supply Report',
        cols: ['PS Node', 'Volts', 'Load A', 'Actives', 'Lowest V', 'At Node'],
        rows: pw ? pw.supplies.map(s => [s.node, s.volts, s.amps.toFixed(2), s.actives, r1(s.vmin), s.vminAt]) : [],
      },
      errors: {
        title: 'Network Test',
        cols: ['Node', 'Severity', 'Type', 'Message'],
        rows: result.errors.map(e => [e.node, e.sev === 'red' ? 'Out of spec' : 'Marginal', e.field, e.msg]),
      },
    };
  }

  return { calc, parseEquip, formatEquip, optimizePS, lockSelections, unlockTaps, reports, combine };
})();

if (typeof module === 'object') module.exports = Engine;
