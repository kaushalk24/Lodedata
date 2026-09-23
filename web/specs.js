/* Sample spec files and sample network.
 * All equipment values are ILLUSTRATIVE placeholders: replace them with your
 * manufacturers' datasheet values (Specs menu) before designing real plant. */

const SAMPLE_SPECS = (() => {
  // Tap families: [value, thru loss @Hi, thru loss @Lo]; the last entry is terminating.
  const families = {
    2: [[32, 0.8, 0.4], [29, 0.8, 0.4], [26, 0.8, 0.5], [23, 0.9, 0.5], [20, 1.0, 0.6],
        [17, 1.2, 0.7], [14, 1.5, 0.9], [11, 2.2, 1.3], [8, 3.4, 2.2], [4]],
    4: [[32, 0.9, 0.5], [29, 0.9, 0.5], [26, 1.0, 0.6], [23, 1.2, 0.7], [20, 1.5, 0.8],
        [17, 2.0, 1.1], [14, 2.8, 1.6], [11, 3.6, 2.4], [8]],
    8: [[32, 1.0, 0.6], [29, 1.1, 0.6], [26, 1.2, 0.7], [23, 1.4, 0.8], [20, 1.8, 1.0],
        [17, 2.8, 1.6], [14, 4.0, 2.4], [11]],
  };
  const taps = [];
  for (const [ports, rows] of Object.entries(families)) {
    for (const [value, hi, lo] of rows) {
      const term = hi === undefined;
      taps.push({
        tsg: 1, part: `T${ports}-${value}${term ? 'T' : ''}`, value, ports: Number(ports), term,
        tapHi: value, tapLo: value, tapRh: value, tapRl: value,
        thruHi: term ? '' : hi, thruLo: term ? '' : lo,
        thruRh: term ? '' : lo, thruRl: term ? '' : Math.max(0.2, Math.round((lo - 0.1) * 10) / 10),
        maxAmps: 15,
      });
    }
  }

  const le = (id, name) => ({
    id, name, part: 'LE-1G', type: 'LE', cascade: id,
    gainHi: 35, gainLo: 33, outHi: 46, outLo: 34, minIn: 14, reserve: 2,
    nf: 9, ctb: 70, cso: 68, refOut: 46, vi: '40:1.10 55:0.85 70:0.70', maxAmps: 15,
  });

  return {
    name: 'SAMPLE',
    parameters: {
      fHi: 1002, fLo: 54, fRh: 42, fRl: 5,
      minTapHi: 16, minTapLo: 5, tapWindow: 10,
      retInRh: 15, retInRl: 15, maxRetRh: 48, maxRetRl: 48,
      allowOverEq: false, maxLeCascade: 2, defaultTsg: 1,
      padMax: 20, padStep: 1, eqValues: '0 2 4 6 8 10 12 14 16 18', eqLoss: 1.0,
      startCN: 51, startCTB: 65, startCSO: 64, minCN: 46, minCTB: 53, minCSO: 53,
      cnAdd: 10, ctbAdd: 20, ctbDerate: 2, csoAdd: 15, csoDerate: 1,
      psVolts: 90, psMaxAmps: 15,
    },
    cables: [
      { id: '1', name: '.750 HARDLINE', hi: 1.10, lo: 0.25, rh: 0.22, rl: 0.08, loop: 0.84 },
      { id: '2', name: '.625 HARDLINE', hi: 1.32, lo: 0.30, rh: 0.27, rl: 0.09, loop: 1.15 },
      { id: '3', name: '.500 HARDLINE', hi: 1.55, lo: 0.36, rh: 0.32, rl: 0.11, loop: 1.60 },
      { id: '9', name: 'FIBER / NO POWER', hi: 0, lo: 0, rh: 0, rl: 0, loop: 99 },
    ],
    actives: [
      { id: '1', name: 'MINI BRIDGER', part: 'MB-1G', type: 'AMP', cascade: '',
        gainHi: 38, gainLo: 36, outHi: 49, outLo: 37, minIn: 15, reserve: 2,
        nf: 8, ctb: 68, cso: 66, refOut: 49, vi: '40:1.60 55:1.25 70:1.00', maxAmps: 15 },
      le('11', 'LE 1 OF 1'), le('21', 'LE 1 OF 2'), le('22', 'LE 2 OF 2'),
      le('31', 'LE 1 OF 3'), le('32', 'LE 2 OF 3'), le('33', 'LE 3 OF 3'),
    ],
    taps,
    couplers: [
      { id: '2', part: 'SPLIT-2', thruHi: 4.2, thruLo: 3.6, thruRh: 3.6, thruRl: 3.5,
        tapHi: 4.2, tapLo: 3.6, tapRh: 3.6, tapRl: 3.5, maxAmps: 15 },
      { id: '8', part: 'DC-8', thruHi: 2.0, thruLo: 1.2, thruRh: 1.2, thruRl: 1.1,
        tapHi: 8.5, tapLo: 8.0, tapRh: 8.0, tapRl: 8.0, maxAmps: 15 },
      { id: '12', part: 'DC-12', thruHi: 1.3, thruLo: 0.7, thruRh: 0.7, thruRl: 0.6,
        tapHi: 12.5, tapLo: 12.0, tapRh: 12.0, tapRl: 12.0, maxAmps: 15 },
      { id: '16', part: 'DC-16', thruHi: 1.0, thruLo: 0.5, thruRh: 0.5, thruRl: 0.5,
        tapHi: 16.5, tapLo: 16.0, tapRh: 16.0, tapRl: 16.0, maxAmps: 15 },
    ],
  };
})();

const SAMPLE_NETWORK = (() => {
  const row = (cbl, ft, hc, eq) => ({ cbl, ft, hc, tsg: 0, eq });
  return {
    name: 'SAMPLE01',
    start: { hi: 49.0, lo: 37.0 }, // level fed into branch 1 (e.g. a bridger port)
    branches: {
      1: [
        row('2', 180, 4, '[*]'), row('2', 150, 3, '[*] *[2]'), row('2', 160, 4, '[*] PS'),
        row('2', 140, 2, '[*]'), row('2', 170, 4, '[*]'), row('2', 150, 0, '21'),
        row('3', 150, 4, '[*]'), row('3', 140, 6, '{*}'), row('3', 130, 3, '[*]'),
        row('3', 120, 2, '(*)'), row('3', 150, 4, '[*]'), row('3', 140, 0, '22'),
        row('3', 150, 4, '[*]'), row('3', 120, 3, '[*]'), row('3', 110, 2, '(*)'),
      ],
      2: [row('3', 90, 3, '[*]'), row('3', 120, 4, '[*]'), row('3', 110, 2, '(*)')],
    },
  };
})();

if (typeof module === 'object') module.exports = { SAMPLE_SPECS, SAMPLE_NETWORK };
