// Run from the repo root: node --test
const test = require('node:test');
const assert = require('node:assert/strict');
const Engine = require('./engine.js');
const { SAMPLE_SPECS, SAMPLE_NETWORK } = require('./specs.js');

const clone = x => JSON.parse(JSON.stringify(x));
const row = (cbl, ft, eq, hc = 4) => ({ cbl, ft, hc, tsg: 0, eq });

test('parses Lode-style equipment notation', () => {
  const eq = Engine.parseEquip('11 [26] (*) -8[3] *[4] PS');
  assert.equal(eq.active, '11');
  assert.deepEqual(eq.taps, [{ ports: 4, value: 26 }, { ports: 2, value: null }]);
  assert.deepEqual(eq.couplers, [{ id: '8', branch: '3', neg: true }, { id: null, branch: '4', neg: false }]);
  assert.equal(eq.ps, true);
  assert.deepEqual(eq.errors, []);
  assert.equal(Engine.formatEquip(eq), '11 [26] (*) -8[3] *[4] PS');
});

test('worked example in docs/02 §3.6: greedy tap selection', () => {
  const net = {
    start: { hi: 46, lo: 34 },
    branches: { 1: [150, 125, 140, 130, 120, 120].map(ft => row('3', ft, '[*]')) },
  };
  const r = Engine.calc(net, SAMPLE_SPECS);
  const taps = r.order.map(id => r.nodes.get(id).taps[0]);
  assert.deepEqual(taps.map(t => t.value), [26, 23, 20, 17, 11, 8]);
  assert.equal(taps[4].port.hi.toFixed(2), '18.99'); // a 14 would give 15.99 < 16
  assert.equal(taps[5].spec.term, true);
  assert.deepEqual(r.errors, []);
});

test('cascade addition: C/N 10·log, CTB 20·log', () => {
  assert.equal(Engine.combine([61, 61, 61], 10).toFixed(1), '56.2');
  assert.equal(Engine.combine([70, 70, 70], 20).toFixed(1), '60.5');
});

test('powering: voltage drop over loop resistance (docs/02 §7.2)', () => {
  const specs = clone(SAMPLE_SPECS);
  specs.actives.find(a => a.id === '11').vi = '0:0.8'; // constant 0.8 A for the hand check
  specs.cables.find(c => c.id === '3').loop = 1.6;
  const net = {
    start: { hi: 46, lo: 34 },
    branches: { 1: [row('3', 0, 'PS', 0), row('3', 1000, '11', 0), row('3', 1000, '11', 0)] },
  };
  const r = Engine.calc(net, specs);
  assert.equal(r.power.nodes.get('1.2').volts.toFixed(2), '87.44');
  assert.equal(r.power.nodes.get('1.3').volts.toFixed(2), '86.16');
});

test('LE cascade IDs: an 11 followed by another LE is out of cascade', () => {
  const net = {
    start: { hi: 46, lo: 34 },
    branches: { 1: [row('3', 600, '11', 0), row('3', 600, '11', 0)] },
  };
  const r = Engine.calc(net, SAMPLE_SPECS);
  assert.ok(r.errors.some(e => e.field === 'cascade' && e.node === '1.1'));
});

test('sample network designs clean', () => {
  const r = Engine.calc(SAMPLE_NETWORK, SAMPLE_SPECS);
  assert.deepEqual(r.errors, []);
  assert.equal(r.nodes.get('1.2').couplers[0].id, '8');
});

test('lock writes auto selections into the equipment text', () => {
  const net = clone(SAMPLE_NETWORK);
  Engine.lockSelections(net, Engine.calc(net, SAMPLE_SPECS));
  assert.equal(net.branches[1][1].eq, '[26] 8[2]');
  Engine.unlockTaps(net);
  assert.equal(net.branches[1][1].eq, '[*] 8[2]');
});

test('a starved thru side does not steal signal from the branch', () => {
  const net = clone(SAMPLE_NETWORK);
  net.branches[1][3].eq = '[29]'; // fixed tap far too high for its input
  const r = Engine.calc(net, SAMPLE_SPECS);
  assert.ok(!r.errors.some(e => e.field === 'coupler'));
  assert.ok(r.errors.some(e => e.node === '1.4' && e.field === 'tap'));
  assert.ok(!r.errors.some(e => e.node.startsWith('2.')));
});
