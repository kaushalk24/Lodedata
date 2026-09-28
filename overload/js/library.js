/* Built-in exercise library (ordered by popularity), muscle groups, workout templates,
 * and a keyword-based muscle guesser so custom exercises rarely end up "unassigned". */

import { norm } from './util.js';

export const MUSCLES = {
  chest: 'Chest', shoulders: 'Shoulders', biceps: 'Biceps', triceps: 'Triceps', forearms: 'Forearms',
  back: 'Back', traps: 'Traps', lowerback: 'Lower Back', abs: 'Abs', obliques: 'Obliques',
  glutes: 'Glutes', quads: 'Quads', hamstrings: 'Hamstrings', adductors: 'Adductors', abductors: 'Abductors', calves: 'Calves',
};
export const MUSCLE_IDS = Object.keys(MUSCLES);

export const EQUIPMENT = {
  barbell: 'Barbell', dumbbell: 'Dumbbell', cable: 'Cable', machine: 'Machine', smith: 'Smith machine',
  bodyweight: 'Bodyweight', kettlebell: 'Kettlebell', band: 'Band', other: 'Other',
};

// [name, primary muscles, secondary muscles, equipment]
const RAW = [
  ['Barbell Bench Press', 'chest', 'triceps shoulders', 'barbell'],
  ['Barbell Squat', 'quads glutes', 'hamstrings lowerback', 'barbell'],
  ['Deadlift', 'hamstrings glutes lowerback', 'back traps forearms', 'barbell'],
  ['Lat Pulldown', 'back', 'biceps', 'cable'],
  ['Dumbbell Shoulder Press', 'shoulders', 'triceps', 'dumbbell'],
  ['Overhead Press', 'shoulders', 'triceps traps', 'barbell'],
  ['Pull-Up', 'back', 'biceps forearms', 'bodyweight'],
  ['Seated Cable Row', 'back', 'biceps shoulders', 'cable'],
  ['Leg Press', 'quads glutes', 'hamstrings', 'machine'],
  ['Dumbbell Lateral Raise', 'shoulders', '', 'dumbbell'],
  ['Incline Dumbbell Bench Press', 'chest', 'shoulders triceps', 'dumbbell'],
  ['Dumbbell Bench Press', 'chest', 'triceps shoulders', 'dumbbell'],
  ['Tricep Pushdown', 'triceps', '', 'cable'],
  ['Dumbbell Bicep Curl', 'biceps', 'forearms', 'dumbbell'],
  ['Romanian Deadlift', 'hamstrings glutes', 'lowerback', 'barbell'],
  ['Leg Extension', 'quads', '', 'machine'],
  ['Lying Leg Curl', 'hamstrings', 'calves', 'machine'],
  ['Barbell Row', 'back', 'biceps lowerback', 'barbell'],
  ['Hip Thrust', 'glutes', 'hamstrings', 'barbell'],
  ['Incline Barbell Bench Press', 'chest', 'shoulders triceps', 'barbell'],
  ['Hammer Curl', 'biceps forearms', '', 'dumbbell'],
  ['Cable Lateral Raise', 'shoulders', '', 'cable'],
  ['Face Pull', 'shoulders', 'traps back', 'cable'],
  ['Chest Press Machine', 'chest', 'triceps shoulders', 'machine'],
  ['Machine Pec Fly', 'chest', 'shoulders', 'machine'],
  ['Cable Chest Fly (High To Low)', 'chest', '', 'cable'],
  ['Cable Chest Fly (Low To High)', 'chest', 'shoulders', 'cable'],
  ['Overhead Triceps Extension (Rope)', 'triceps', '', 'cable'],
  ['Barbell Curl', 'biceps', 'forearms', 'barbell'],
  ['Seated Calf Raise', 'calves', '', 'machine'],
  ['Standing Calf Raise', 'calves', '', 'machine'],
  ['Hack Squat', 'quads', 'glutes', 'machine'],
  ['Bulgarian Split Squat', 'quads glutes', 'hamstrings adductors', 'dumbbell'],
  ['Walking Lunge', 'quads glutes', 'hamstrings', 'dumbbell'],
  ['Barbell Lunge', 'quads glutes', 'hamstrings adductors', 'barbell'],
  ['Goblet Squat', 'quads glutes', 'abs', 'dumbbell'],
  ['Seated Leg Curl', 'hamstrings', '', 'machine'],
  ['Hip Adduction Machine', 'adductors', '', 'machine'],
  ['Hip Abduction Machine', 'abductors', 'glutes', 'machine'],
  ['Chin-Up', 'back biceps', 'forearms', 'bodyweight'],
  ['Dips', 'triceps chest', 'shoulders', 'bodyweight'],
  ['Push-Up', 'chest', 'triceps shoulders abs', 'bodyweight'],
  ['Plank', 'abs', 'obliques shoulders', 'bodyweight'],
  ['Hanging Knee Raise', 'abs', 'obliques', 'bodyweight'],
  ['Hanging Leg Raise', 'abs', 'obliques forearms', 'bodyweight'],
  ['Cable Crunch', 'abs', '', 'cable'],
  ['Russian Twist', 'obliques', 'abs', 'bodyweight'],
  ['Barbell Shrug', 'traps', 'forearms', 'barbell'],
  ['Dumbbell Shrug', 'traps', 'forearms', 'dumbbell'],
  ['Rear Delt Fly Machine', 'shoulders', 'back traps', 'machine'],
  ['Dumbbell Rear Delt Fly', 'shoulders', 'back', 'dumbbell'],
  ['Single Arm Dumbbell Row', 'back', 'biceps', 'dumbbell'],
  ['Chest Supported Row', 'back', 'biceps shoulders', 'machine'],
  ['T-Bar Row', 'back', 'biceps lowerback', 'barbell'],
  ['Machine Row', 'back', 'biceps', 'machine'],
  ['Close Grip Lat Pulldown', 'back', 'biceps', 'cable'],
  ['Straight Arm Pulldown', 'back', 'triceps', 'cable'],
  ['Cable Pullover', 'back', 'chest triceps', 'cable'],
  ['Dumbbell Pullover', 'back chest', 'triceps', 'dumbbell'],
  ['Assisted Pull-Up', 'back', 'biceps', 'machine'],
  ['Back Extension', 'lowerback glutes', 'hamstrings', 'bodyweight'],
  ['Good Morning', 'hamstrings lowerback', 'glutes', 'barbell'],
  ['Sumo Deadlift', 'glutes quads adductors', 'hamstrings lowerback', 'barbell'],
  ['Trap Bar Deadlift', 'quads glutes hamstrings', 'lowerback traps', 'barbell'],
  ['Front Squat', 'quads', 'glutes abs', 'barbell'],
  ['Smith Machine Squat', 'quads glutes', 'hamstrings', 'smith'],
  ['Smith Machine Bench Press', 'chest', 'triceps shoulders', 'smith'],
  ['Incline Smith Machine Press', 'chest', 'shoulders triceps', 'smith'],
  ['Smith Machine Shoulder Press', 'shoulders', 'triceps', 'smith'],
  ['Machine Shoulder Press', 'shoulders', 'triceps', 'machine'],
  ['Arnold Press', 'shoulders', 'triceps', 'dumbbell'],
  ['Front Raise', 'shoulders', '', 'dumbbell'],
  ['Upright Row', 'shoulders traps', 'biceps', 'barbell'],
  ['Decline Bench Press', 'chest', 'triceps', 'barbell'],
  ['Dumbbell Fly', 'chest', 'shoulders', 'dumbbell'],
  ['Incline Dumbbell Fly', 'chest', 'shoulders', 'dumbbell'],
  ['Pec Deck', 'chest', '', 'machine'],
  ['Hammer Strength Chest Press', 'chest', 'triceps shoulders', 'machine'],
  ['Iso-Lateral Incline Press', 'chest', 'shoulders triceps', 'machine'],
  ['Close Grip Bench Press', 'triceps', 'chest shoulders', 'barbell'],
  ['Skull Crusher', 'triceps', '', 'barbell'],
  ['JM Press', 'triceps', 'chest', 'barbell'],
  ['Single Arm Tricep Pushdown', 'triceps', '', 'cable'],
  ['V Bar Tricep Pushdown', 'triceps', '', 'cable'],
  ['Dumbbell Overhead Triceps Extension', 'triceps', '', 'dumbbell'],
  ['Tricep Kickback', 'triceps', '', 'dumbbell'],
  ['Tricep Extension Machine', 'triceps', '', 'machine'],
  ['Preacher Curl', 'biceps', 'forearms', 'barbell'],
  ['Machine Preacher Curl', 'biceps', '', 'machine'],
  ['Incline Dumbbell Curl', 'biceps', '', 'dumbbell'],
  ['Concentration Curl', 'biceps', '', 'dumbbell'],
  ['Cable Curl', 'biceps', 'forearms', 'cable'],
  ['Bayesian Cable Curl', 'biceps', '', 'cable'],
  ['EZ Bar Curl', 'biceps', 'forearms', 'barbell'],
  ['Spider Curl', 'biceps', '', 'dumbbell'],
  ['Reverse Curl', 'forearms', 'biceps', 'barbell'],
  ['Wrist Curl', 'forearms', '', 'dumbbell'],
  ['Reverse Wrist Curl', 'forearms', '', 'dumbbell'],
  ["Farmer's Carry", 'forearms traps', 'abs glutes', 'dumbbell'],
  ['Kettlebell Swing', 'glutes hamstrings', 'lowerback shoulders', 'kettlebell'],
  ['Kettlebell Goblet Squat', 'quads glutes', 'abs', 'kettlebell'],
  ['Dumbbell Push Press', 'shoulders', 'triceps quads', 'dumbbell'],
  ['Dumbbell Thruster', 'quads shoulders', 'glutes triceps', 'dumbbell'],
  ['Power Clean', 'glutes hamstrings traps', 'quads shoulders', 'barbell'],
  ['Box Jump', 'quads glutes', 'calves', 'bodyweight'],
  ['Burpee', 'quads chest', 'shoulders abs', 'bodyweight'],
  ['Mountain Climber', 'abs', 'shoulders quads', 'bodyweight'],
  ['Step-Up', 'quads glutes', 'hamstrings', 'dumbbell'],
  ['Reverse Lunge', 'quads glutes', 'hamstrings', 'dumbbell'],
  ['Glute Bridge', 'glutes', 'hamstrings', 'bodyweight'],
  ['Cable Kickback', 'glutes', 'hamstrings', 'cable'],
  ['Standing Leg Curl', 'hamstrings', '', 'machine'],
  ['Nordic Curl', 'hamstrings', '', 'bodyweight'],
  ['Pendulum Squat', 'quads', 'glutes', 'machine'],
  ['Sissy Squat', 'quads', '', 'bodyweight'],
  ['Leg Raise', 'abs', 'obliques', 'bodyweight'],
  ['Crunch', 'abs', '', 'bodyweight'],
  ['Ab Wheel Rollout', 'abs', 'shoulders lowerback', 'other'],
  ['Cable Woodchop', 'obliques', 'abs shoulders', 'cable'],
  ['Side Plank', 'obliques', 'abs', 'bodyweight'],
  ['Medball Halo', 'shoulders abs', '', 'other'],
  ['Inverted Row', 'back', 'biceps', 'bodyweight'],
  ['Band Pull-Apart', 'shoulders', 'traps back', 'band'],
  ['Pike Push-Up', 'shoulders', 'triceps', 'bodyweight'],
  ['Diamond Push-Up', 'triceps chest', 'shoulders', 'bodyweight'],
  ['Bodyweight Squat', 'quads glutes', '', 'bodyweight'],
  ['Single Leg Romanian Deadlift', 'hamstrings glutes', 'lowerback', 'dumbbell'],
  ['Dumbbell Romanian Deadlift', 'hamstrings glutes', 'lowerback', 'dumbbell'],
  ['Dumbbell Row', 'back', 'biceps', 'dumbbell'],
  ['Calf Press on Leg Press', 'calves', '', 'machine'],
];

const slug = s => norm(s).replace(/ /g, '-');
export const LIBRARY = RAW.map(([name, p, s, eq], i) => ({
  id: slug(name), name, primary: p.split(' ').filter(Boolean), secondary: s.split(' ').filter(Boolean), equipment: eq, rank: i,
}));
export const LIB_BY_ID = Object.fromEntries(LIBRARY.map(e => [e.id, e]));
export const libByName = name => LIBRARY.find(e => norm(e.name) === norm(name));

export const TEMPLATES = [
  { id: 'upper', name: 'Grow Your Upper Body', color: 'blue', desc: '3-4 sets of 8-12 reps. Rest about 2 minutes.',
    exercises: ['Incline Barbell Bench Press', 'Seated Cable Row', 'Dumbbell Shoulder Press', 'Lat Pulldown', 'Cable Lateral Raise', 'Tricep Pushdown', 'Dumbbell Bicep Curl'] },
  { id: 'burn', name: 'Burn Fat & Boost Endurance', color: 'orange', desc: 'Circuit: 12-15 reps each, move quickly, rest 60 s after each round.',
    exercises: ['Goblet Squat', 'Kettlebell Swing', 'Dumbbell Push Press', 'Push-Up', 'Walking Lunge', 'Mountain Climber', 'Plank'] },
  { id: 'legs', name: 'Build Powerful Legs & Glutes', color: 'pink', desc: '3-4 sets of 6-12 reps. Rest 2-3 minutes on the first two lifts.',
    exercises: ['Barbell Lunge', 'Leg Press', 'Leg Extension', 'Romanian Deadlift', 'Hip Thrust', 'Lying Leg Curl', 'Standing Calf Raise'] },
  { id: 'strength', name: 'Starting Strength', color: 'red', desc: '3 sets of 5 (deadlift 1x5). Add weight every session while form holds.',
    exercises: ['Barbell Squat', 'Barbell Bench Press', 'Overhead Press', 'Deadlift', 'Power Clean', 'Barbell Row'] },
];

// Ordered: the first rule that matches wins, so specific phrases come before generic words.
const RULES = [
  [/calf|calves/, 'calves', ''],
  [/leg curl|hamstring|nordic|\brdl\b|romanian|stiff leg|good morning/, 'hamstrings glutes', ''],
  [/hip thrust|glute|bridge/, 'glutes', 'hamstrings'],
  [/adduct/, 'adductors', ''],
  [/abduct/, 'abductors', 'glutes'],
  [/deadlift/, 'hamstrings glutes lowerback', 'back traps forearms'],
  [/leg extension|squat|leg press|lunge|hack|step up|split/, 'quads glutes', 'hamstrings'],
  [/back extension|hyperextension|lower back/, 'lowerback', 'glutes'],
  [/forearm|wrist|grip|farmer/, 'forearms', ''],
  [/hammer curl|reverse curl/, 'biceps forearms', ''],
  [/curl|bicep/, 'biceps', 'forearms'],
  [/tricep|pushdown|push down|skull|\bjm\b|kickback|\bdips?\b|extension/, 'triceps', ''],
  [/rear delt|rare delt|reverse fly|face pull/, 'shoulders', 'back traps'],
  [/lateral raise|front raise|shoulder|overhead press|\bohp\b|military|arnold|delt|upright row/, 'shoulders', 'triceps'],
  [/shrug|trap/, 'traps', ''],
  [/bench|chest|pec|fly|flye|push ?up|press machine/, 'chest', 'triceps shoulders'],
  [/row|pulldown|pull down|pull ?up|chin|\blat\b|pullover|pull over/, 'back', 'biceps'],
  [/crunch|plank|leg raise|knee raise|sit ?up|\babs?\b|rollout/, 'abs', 'obliques'],
  [/twist|oblique|woodchop|side bend/, 'obliques', 'abs'],
];

/** Guess muscles for a custom exercise name. Library names match exactly first. */
export function guessMuscles(name) {
  const lib = libByName(name);
  if (lib) return { primary: lib.primary, secondary: lib.secondary, equipment: lib.equipment };
  const n = ' ' + norm(name) + ' ';
  for (const [re, p, s] of RULES) {
    if (re.test(n)) return { primary: p.split(' '), secondary: s ? s.split(' ') : [], equipment: guessEquipment(n) };
  }
  return { primary: [], secondary: [], equipment: guessEquipment(n) };
}
function guessEquipment(n) {
  if (/smith/.test(n)) return 'smith';
  if (/dumbbell|dumbell|\bdb\b/.test(n)) return 'dumbbell';
  if (/barbell|\bbb\b|\bez\b/.test(n)) return 'barbell';
  if (/cable|rope|pushdown|pulldown/.test(n)) return 'cable';
  if (/machine|press machine|iso lateral|hammer strength|leg press|leg extension|leg curl/.test(n)) return 'machine';
  if (/kettlebell|\bkb\b/.test(n)) return 'kettlebell';
  if (/pull ?up|push ?up|chin|dip|plank|bodyweight/.test(n)) return 'bodyweight';
  return 'other';
}
