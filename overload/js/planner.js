/* Offline "Design your plan": picks a split from days/week, fills each day with movement
 * patterns, maps patterns to exercises for the available equipment, and applies a set/rep/rest
 * scheme for the goal. Deterministic and free, no AI service. */

// movement slot -> exercise for [gym, dumbbells, bodyweight]
const SLOT = {
  squat: ['Barbell Squat', 'Goblet Squat', 'Bodyweight Squat'],
  legpress: ['Leg Press', 'Bulgarian Split Squat', 'Bulgarian Split Squat'],
  hinge: ['Romanian Deadlift', 'Dumbbell Romanian Deadlift', 'Single Leg Romanian Deadlift'],
  deadlift: ['Deadlift', 'Dumbbell Romanian Deadlift', 'Glute Bridge'],
  lunge: ['Walking Lunge', 'Walking Lunge', 'Reverse Lunge'],
  legcurl: ['Lying Leg Curl', 'Single Leg Romanian Deadlift', 'Nordic Curl'],
  legext: ['Leg Extension', 'Step-Up', 'Sissy Squat'],
  glute: ['Hip Thrust', 'Glute Bridge', 'Glute Bridge'],
  calf: ['Standing Calf Raise', 'Standing Calf Raise', 'Standing Calf Raise'],
  hpress: ['Barbell Bench Press', 'Dumbbell Bench Press', 'Push-Up'],
  ipress: ['Incline Dumbbell Bench Press', 'Incline Dumbbell Bench Press', 'Dips'],
  vpress: ['Overhead Press', 'Dumbbell Shoulder Press', 'Pike Push-Up'],
  fly: ['Cable Chest Fly (High To Low)', 'Dumbbell Fly', 'Diamond Push-Up'],
  lateral: ['Cable Lateral Raise', 'Dumbbell Lateral Raise', null],
  vpull: ['Lat Pulldown', 'Pull-Up', 'Pull-Up'],
  hpull: ['Seated Cable Row', 'Single Arm Dumbbell Row', 'Inverted Row'],
  row2: ['Chest Supported Row', 'Dumbbell Row', 'Inverted Row'],
  reardelt: ['Face Pull', 'Dumbbell Rear Delt Fly', 'Band Pull-Apart'],
  biceps: ['Cable Curl', 'Dumbbell Bicep Curl', 'Chin-Up'],
  hammer: ['Hammer Curl', 'Hammer Curl', null],
  triceps: ['Tricep Pushdown', 'Dumbbell Overhead Triceps Extension', 'Diamond Push-Up'],
  triceps2: ['Overhead Triceps Extension (Rope)', 'Tricep Kickback', 'Dips'],
  core: ['Cable Crunch', 'Plank', 'Plank'],
  core2: ['Hanging Leg Raise', 'Russian Twist', 'Mountain Climber'],
  power: ['Power Clean', 'Dumbbell Thruster', 'Box Jump'],
  jump: ['Box Jump', 'Box Jump', 'Burpee'],
  carry: ["Farmer's Carry", "Farmer's Carry", 'Plank'],
};
const EQ_INDEX = { gym: 0, dumbbells: 1, bodyweight: 2 };

// Big lifts first so they get the fresh sets and the longest rest.
const DAYS = {
  fullA: ['Full Body A', ['squat', 'hpress', 'hpull', 'legcurl', 'lateral', 'core'], 'lower'],
  fullB: ['Full Body B', ['deadlift', 'vpress', 'vpull', 'lunge', 'biceps', 'triceps'], 'lower'],
  fullC: ['Full Body C', ['legpress', 'ipress', 'row2', 'glute', 'reardelt', 'core2'], 'lower'],
  push: ['Push', ['hpress', 'ipress', 'vpress', 'lateral', 'triceps', 'triceps2'], 'upper'],
  pull: ['Pull', ['vpull', 'hpull', 'row2', 'reardelt', 'biceps', 'hammer'], 'upper'],
  legs: ['Legs', ['squat', 'hinge', 'legpress', 'legcurl', 'legext', 'calf'], 'lower'],
  upperA: ['Upper A', ['hpress', 'hpull', 'vpress', 'vpull', 'biceps', 'triceps'], 'upper'],
  upperB: ['Upper B', ['ipress', 'row2', 'lateral', 'fly', 'hammer', 'triceps2'], 'upper'],
  lowerA: ['Lower A', ['squat', 'legcurl', 'lunge', 'calf', 'core'], 'lower'],
  lowerB: ['Lower B', ['deadlift', 'legpress', 'legext', 'glute', 'core2'], 'lower'],
};

export function chooseSplit(days, level) {
  switch (days) {
    case 2: return ['fullA', 'fullB'];
    case 3: return level === 'beginner' ? ['fullA', 'fullB', 'fullC'] : ['push', 'pull', 'legs'];
    case 4: return ['upperA', 'lowerA', 'upperB', 'lowerB'];
    case 5: return ['push', 'pull', 'legs', 'upperA', 'lowerB'];
    default: return ['push', 'pull', 'legs', 'push', 'pull', 'legs'];
  }
}

// Scheme per exercise position: [sets, reps, restSec]
const SCHEMES = {
  physique: (i) => i === 0 ? [4, '6-10', 150] : i < 3 ? [3, '8-12', 120] : [3, '10-15', 75],
  strength: (i) => i === 0 ? [5, '3-5', 180] : i === 1 ? [4, '4-6', 180] : [3, '6-10', 120],
  athletic: (i) => i === 0 ? [4, '3-5', 150] : i < 3 ? [4, '5-8', 120] : [3, '8-12', 75],
  general: (i) => i < 2 ? [3, '8-12', 90] : [3, '12-15', 60],
};

export const GOALS = {
  physique: { name: 'Physique', blurb: 'Build muscle where you want it.' },
  strength: { name: 'Strength', blurb: 'Lift heavier on the big compound lifts.' },
  athletic: { name: 'Athletic Performance', blurb: 'Power, speed and resilience for your sport.' },
  general: { name: 'General Fitness', blurb: 'Feel fit, move well, stay consistent.' },
};

const PROGRESSION = {
  physique: 'Add a rep each session. When every set reaches the top of the range, add the smallest weight step and start again at the bottom.',
  strength: 'Add 2.5 kg to the main lift each week while every rep stays clean. After two stalled sessions, drop 10% and build back.',
  athletic: 'Keep power work fast and crisp and stop a set before speed drops. Progress the strength lifts like a strength plan.',
  general: 'Aim for 1-2 reps in reserve on each set. Add weight when 15 reps feels easy.',
};

/**
 * @param {{goal:string, days:number, equipment:'gym'|'dumbbells'|'bodyweight', level:'beginner'|'intermediate'}} o
 * @returns {{name:string, progression:string, days:{name:string, exercises:{name:string, sets:number, reps:string, rest:number}[]}[]}}
 */
export function generatePlan({ goal = 'physique', days = 3, equipment = 'gym', level = 'beginner' } = {}) {
  days = Math.min(6, Math.max(2, Math.round(days)));
  const eq = EQ_INDEX[equipment] ?? 0;
  const scheme = SCHEMES[goal] || SCHEMES.physique;
  const split = chooseSplit(days, level);
  const seen = {};
  const out = split.map(key => {
    const [baseName, slots, kind] = DAYS[key];
    seen[baseName] = (seen[baseName] || 0) + 1;
    let list = [...slots];
    if (goal === 'athletic') {
      list = [kind === 'lower' ? 'jump' : 'power', ...list];
      if (kind === 'lower') list.push('carry');
    }
    const cap = level === 'beginner' ? 5 : 6 + (goal === 'athletic' ? 1 : 0);
    const names = [];
    for (const slot of list) {
      const name = SLOT[slot]?.[eq];
      if (name && !names.includes(name)) names.push(name);
      if (names.length >= cap) break;
    }
    return {
      name: baseName, key,
      exercises: names.map((name, i) => {
        const [sets, reps, rest] = scheme(i);
        return { name, sets: level === 'beginner' ? Math.min(sets, 3) : sets, reps, rest };
      }),
    };
  });
  // Repeated day names get numbered: "Push 1", "Push 2".
  const count = {};
  for (const d of out) if (seen[d.name] > 1) d.name = `${d.name} ${(count[d.name] = (count[d.name] || 0) + 1)}`;
  return {
    name: `${GOALS[goal]?.name || 'Custom'} · ${days} days`,
    progression: PROGRESSION[goal] || PROGRESSION.physique,
    days: out,
  };
}

const fmtRest = s => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
export const planDayText = (day, progression) =>
  day.exercises.map(e => `${e.name}: ${e.sets} × ${e.reps}, rest ${fmtRest(e.rest)}`).join('\n') + (progression ? `\n\n${progression}` : '');
