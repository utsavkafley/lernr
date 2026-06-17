// A compact Spanish conjugation engine.
//
// It covers, for the six tenses the UI exposes:
//   • regular -ar / -er / -ir verbs,
//   • a table of fully-irregular high-frequency verbs,
//   • systematic stem changes (e>ie, o>ue, e>i, u>ue) in the present, the
//     present subjunctive and (for -ir verbs) the 3rd-person preterite,
//   • the regular orthographic spelling changes (-car/-gar/-zar, -ger/-gir,
//     -guir, -cer/-cir) and the y-insertion of -uir / vowel-stem verbs.
//
// It deliberately does NOT chase every defective or accent-only edge case —
// marked verbs (★ in the UI) follow the common patterns above, which is what a
// learner is actually trying to internalise here.

export type Tense =
  | 'present'
  | 'preterite'
  | 'imperfect'
  | 'future'
  | 'conditional'
  | 'subjunctive'

export interface TenseMeta {
  id: Tense
  label: string
  hint: string
}

export const TENSES: TenseMeta[] = [
  { id: 'present', label: 'Present', hint: 'I see' },
  { id: 'preterite', label: 'Preterite', hint: 'I saw' },
  { id: 'imperfect', label: 'Imperfect', hint: 'I used to see' },
  { id: 'future', label: 'Future', hint: 'I will see' },
  { id: 'conditional', label: 'Conditional', hint: 'I would see' },
  { id: 'subjunctive', label: 'Subjunctive', hint: '...that I see' },
]

export interface PersonMeta {
  id: number // 0..5
  pronoun: string
  english: string
}

export const PERSONS: PersonMeta[] = [
  { id: 0, pronoun: 'yo', english: 'I' },
  { id: 1, pronoun: 'tú', english: 'you' },
  { id: 2, pronoun: 'él / ella', english: 'he / she' },
  { id: 3, pronoun: 'nosotros', english: 'we' },
  { id: 4, pronoun: 'vosotros', english: 'you all' },
  { id: 5, pronoun: 'ellos / ellas', english: 'they' },
]

type Six = [string, string, string, string, string, string]
type Group = 'ar' | 'er' | 'ir'

// Regular endings, indexed [person 0..5].
const REGULAR: Record<Tense, Record<Group, Six>> = {
  present: {
    ar: ['o', 'as', 'a', 'amos', 'áis', 'an'],
    er: ['o', 'es', 'e', 'emos', 'éis', 'en'],
    ir: ['o', 'es', 'e', 'imos', 'ís', 'en'],
  },
  preterite: {
    ar: ['é', 'aste', 'ó', 'amos', 'asteis', 'aron'],
    er: ['í', 'iste', 'ió', 'imos', 'isteis', 'ieron'],
    ir: ['í', 'iste', 'ió', 'imos', 'isteis', 'ieron'],
  },
  imperfect: {
    ar: ['aba', 'abas', 'aba', 'ábamos', 'abais', 'aban'],
    er: ['ía', 'ías', 'ía', 'íamos', 'íais', 'ían'],
    ir: ['ía', 'ías', 'ía', 'íamos', 'íais', 'ían'],
  },
  future: {
    ar: ['é', 'ás', 'á', 'emos', 'éis', 'án'],
    er: ['é', 'ás', 'á', 'emos', 'éis', 'án'],
    ir: ['é', 'ás', 'á', 'emos', 'éis', 'án'],
  },
  conditional: {
    ar: ['ía', 'ías', 'ía', 'íamos', 'íais', 'ían'],
    er: ['ía', 'ías', 'ía', 'íamos', 'íais', 'ían'],
    ir: ['ía', 'ías', 'ía', 'íamos', 'íais', 'ían'],
  },
  subjunctive: {
    ar: ['e', 'es', 'e', 'emos', 'éis', 'en'],
    er: ['a', 'as', 'a', 'amos', 'áis', 'an'],
    ir: ['a', 'as', 'a', 'amos', 'áis', 'an'],
  },
}

// Irregular future/conditional stems (these two tenses share one stem).
const FUT_STEM: Record<string, string> = {
  tener: 'tendr', poner: 'pondr', venir: 'vendr', salir: 'saldr',
  poder: 'podr', querer: 'querr', saber: 'sabr', haber: 'habr',
  hacer: 'har', decir: 'dir', caber: 'cabr', valer: 'valdr',
  mantener: 'mantendr', sostener: 'sostendr', detener: 'detendr',
  proponer: 'propondr', suponer: 'supondr',
  // -ír verbs drop the infinitive accent in future/conditional (oiré, reiré…).
  oír: 'oir', reír: 'reir', freír: 'freir', sonreír: 'sonreir',
}

// Stem-vowel changes for the present-tense "boot" (and beyond — see below).
const STEM: Record<string, 'e>ie' | 'o>ue' | 'e>i' | 'u>ue'> = {
  // e > ie
  pensar: 'e>ie', empezar: 'e>ie', comenzar: 'e>ie', cerrar: 'e>ie',
  entender: 'e>ie', perder: 'e>ie', encender: 'e>ie', defender: 'e>ie',
  sentir: 'e>ie', preferir: 'e>ie', mentir: 'e>ie', sugerir: 'e>ie',
  advertir: 'e>ie', recomendar: 'e>ie', confesar: 'e>ie', negar: 'e>ie',
  apretar: 'e>ie', temblar: 'e>ie', sembrar: 'e>ie', regar: 'e>ie',
  calentar: 'e>ie', gobernar: 'e>ie', tropezar: 'e>ie', convertir: 'e>ie',
  despertar: 'e>ie', sentar: 'e>ie', divertir: 'e>ie',
  // o > ue
  contar: 'o>ue', encontrar: 'o>ue', recordar: 'o>ue', mostrar: 'o>ue',
  volver: 'o>ue', mover: 'o>ue', dormir: 'o>ue', morir: 'o>ue',
  soltar: 'o>ue', colgar: 'o>ue', volar: 'o>ue', rodar: 'o>ue',
  soñar: 'o>ue', acostar: 'o>ue', morder: 'o>ue', resolver: 'o>ue',
  acordar: 'o>ue',
  doler: 'o>ue', envolver: 'o>ue', desenvolver: 'o>ue', apostar: 'o>ue',
  probar: 'o>ue', comprobar: 'o>ue', aprobar: 'o>ue', demostrar: 'o>ue',
  esforzar: 'o>ue',
  // e > i
  pedir: 'e>i', servir: 'e>i', repetir: 'e>i', seguir: 'e>i',
  conseguir: 'e>i', perseguir: 'e>i', elegir: 'e>i', corregir: 'e>i',
  rendir: 'e>i', derretir: 'e>i', medir: 'e>i', despedir: 'e>i',
  vestir: 'e>i',
  // u > ue
  jugar: 'u>ue',
}

// Fully irregular verbs: explicit forms per tense. Anything not listed for a
// given verb falls back to the rules below (so we only spell out what breaks).
const IRREGULAR: Record<string, Partial<Record<Tense, Six>>> = {
  ser: {
    present: ['soy', 'eres', 'es', 'somos', 'sois', 'son'],
    preterite: ['fui', 'fuiste', 'fue', 'fuimos', 'fuisteis', 'fueron'],
    imperfect: ['era', 'eras', 'era', 'éramos', 'erais', 'eran'],
    subjunctive: ['sea', 'seas', 'sea', 'seamos', 'seáis', 'sean'],
  },
  estar: {
    present: ['estoy', 'estás', 'está', 'estamos', 'estáis', 'están'],
    preterite: ['estuve', 'estuviste', 'estuvo', 'estuvimos', 'estuvisteis', 'estuvieron'],
    subjunctive: ['esté', 'estés', 'esté', 'estemos', 'estéis', 'estén'],
  },
  ir: {
    present: ['voy', 'vas', 'va', 'vamos', 'vais', 'van'],
    preterite: ['fui', 'fuiste', 'fue', 'fuimos', 'fuisteis', 'fueron'],
    imperfect: ['iba', 'ibas', 'iba', 'íbamos', 'ibais', 'iban'],
    subjunctive: ['vaya', 'vayas', 'vaya', 'vayamos', 'vayáis', 'vayan'],
  },
  haber: {
    present: ['he', 'has', 'ha', 'hemos', 'habéis', 'han'],
    preterite: ['hube', 'hubiste', 'hubo', 'hubimos', 'hubisteis', 'hubieron'],
    subjunctive: ['haya', 'hayas', 'haya', 'hayamos', 'hayáis', 'hayan'],
  },
  tener: {
    present: ['tengo', 'tienes', 'tiene', 'tenemos', 'tenéis', 'tienen'],
    preterite: ['tuve', 'tuviste', 'tuvo', 'tuvimos', 'tuvisteis', 'tuvieron'],
    subjunctive: ['tenga', 'tengas', 'tenga', 'tengamos', 'tengáis', 'tengan'],
  },
  mantener: {
    present: ['mantengo', 'mantienes', 'mantiene', 'mantenemos', 'mantenéis', 'mantienen'],
    preterite: ['mantuve', 'mantuviste', 'mantuvo', 'mantuvimos', 'mantuvisteis', 'mantuvieron'],
    subjunctive: ['mantenga', 'mantengas', 'mantenga', 'mantengamos', 'mantengáis', 'mantengan'],
  },
  hacer: {
    present: ['hago', 'haces', 'hace', 'hacemos', 'hacéis', 'hacen'],
    preterite: ['hice', 'hiciste', 'hizo', 'hicimos', 'hicisteis', 'hicieron'],
    subjunctive: ['haga', 'hagas', 'haga', 'hagamos', 'hagáis', 'hagan'],
  },
  poder: {
    present: ['puedo', 'puedes', 'puede', 'podemos', 'podéis', 'pueden'],
    preterite: ['pude', 'pudiste', 'pudo', 'pudimos', 'pudisteis', 'pudieron'],
    subjunctive: ['pueda', 'puedas', 'pueda', 'podamos', 'podáis', 'puedan'],
  },
  decir: {
    present: ['digo', 'dices', 'dice', 'decimos', 'decís', 'dicen'],
    preterite: ['dije', 'dijiste', 'dijo', 'dijimos', 'dijisteis', 'dijeron'],
    subjunctive: ['diga', 'digas', 'diga', 'digamos', 'digáis', 'digan'],
  },
  ver: {
    present: ['veo', 'ves', 've', 'vemos', 'veis', 'ven'],
    preterite: ['vi', 'viste', 'vio', 'vimos', 'visteis', 'vieron'],
    imperfect: ['veía', 'veías', 'veía', 'veíamos', 'veíais', 'veían'],
    subjunctive: ['vea', 'veas', 'vea', 'veamos', 'veáis', 'vean'],
  },
  dar: {
    present: ['doy', 'das', 'da', 'damos', 'dais', 'dan'],
    preterite: ['di', 'diste', 'dio', 'dimos', 'disteis', 'dieron'],
    subjunctive: ['dé', 'des', 'dé', 'demos', 'deis', 'den'],
  },
  saber: {
    present: ['sé', 'sabes', 'sabe', 'sabemos', 'sabéis', 'saben'],
    preterite: ['supe', 'supiste', 'supo', 'supimos', 'supisteis', 'supieron'],
    subjunctive: ['sepa', 'sepas', 'sepa', 'sepamos', 'sepáis', 'sepan'],
  },
  querer: {
    present: ['quiero', 'quieres', 'quiere', 'queremos', 'queréis', 'quieren'],
    preterite: ['quise', 'quisiste', 'quiso', 'quisimos', 'quisisteis', 'quisieron'],
    subjunctive: ['quiera', 'quieras', 'quiera', 'queramos', 'queráis', 'quieran'],
  },
  poner: {
    present: ['pongo', 'pones', 'pone', 'ponemos', 'ponéis', 'ponen'],
    preterite: ['puse', 'pusiste', 'puso', 'pusimos', 'pusisteis', 'pusieron'],
    subjunctive: ['ponga', 'pongas', 'ponga', 'pongamos', 'pongáis', 'pongan'],
  },
  proponer: {
    present: ['propongo', 'propones', 'propone', 'proponemos', 'proponéis', 'proponen'],
    preterite: ['propuse', 'propusiste', 'propuso', 'propusimos', 'propusisteis', 'propusieron'],
    subjunctive: ['proponga', 'propongas', 'proponga', 'propongamos', 'propongáis', 'propongan'],
  },
  suponer: {
    present: ['supongo', 'supones', 'supone', 'suponemos', 'suponéis', 'suponen'],
    preterite: ['supuse', 'supusiste', 'supuso', 'supusimos', 'supusisteis', 'supusieron'],
    subjunctive: ['suponga', 'supongas', 'suponga', 'supongamos', 'supongáis', 'supongan'],
  },
  venir: {
    present: ['vengo', 'vienes', 'viene', 'venimos', 'venís', 'vienen'],
    preterite: ['vine', 'viniste', 'vino', 'vinimos', 'vinisteis', 'vinieron'],
    subjunctive: ['venga', 'vengas', 'venga', 'vengamos', 'vengáis', 'vengan'],
  },
  salir: {
    present: ['salgo', 'sales', 'sale', 'salimos', 'salís', 'salen'],
    subjunctive: ['salga', 'salgas', 'salga', 'salgamos', 'salgáis', 'salgan'],
  },
  traer: {
    present: ['traigo', 'traes', 'trae', 'traemos', 'traéis', 'traen'],
    preterite: ['traje', 'trajiste', 'trajo', 'trajimos', 'trajisteis', 'trajeron'],
    subjunctive: ['traiga', 'traigas', 'traiga', 'traigamos', 'traigáis', 'traigan'],
  },
  caer: {
    present: ['caigo', 'caes', 'cae', 'caemos', 'caéis', 'caen'],
    preterite: ['caí', 'caíste', 'cayó', 'caímos', 'caísteis', 'cayeron'],
    subjunctive: ['caiga', 'caigas', 'caiga', 'caigamos', 'caigáis', 'caigan'],
  },
  oír: {
    present: ['oigo', 'oyes', 'oye', 'oímos', 'oís', 'oyen'],
    preterite: ['oí', 'oíste', 'oyó', 'oímos', 'oísteis', 'oyeron'],
    subjunctive: ['oiga', 'oigas', 'oiga', 'oigamos', 'oigáis', 'oigan'],
  },
  conducir: {
    present: ['conduzco', 'conduces', 'conduce', 'conducimos', 'conducís', 'conducen'],
    preterite: ['conduje', 'condujiste', 'condujo', 'condujimos', 'condujisteis', 'condujeron'],
    subjunctive: ['conduzca', 'conduzcas', 'conduzca', 'conduzcamos', 'conduzcáis', 'conduzcan'],
  },
  producir: {
    present: ['produzco', 'produces', 'produce', 'producimos', 'producís', 'producen'],
    preterite: ['produje', 'produjiste', 'produjo', 'produjimos', 'produjisteis', 'produjeron'],
    subjunctive: ['produzca', 'produzcas', 'produzca', 'produzcamos', 'produzcáis', 'produzcan'],
  },
  traducir: {
    present: ['traduzco', 'traduces', 'traduce', 'traducimos', 'traducís', 'traducen'],
    preterite: ['traduje', 'tradujiste', 'tradujo', 'tradujimos', 'tradujisteis', 'tradujeron'],
    subjunctive: ['traduzca', 'traduzcas', 'traduzca', 'traduzcamos', 'traduzcáis', 'traduzcan'],
  },
  reducir: {
    present: ['reduzco', 'reduces', 'reduce', 'reducimos', 'reducís', 'reducen'],
    preterite: ['reduje', 'redujiste', 'redujo', 'redujimos', 'redujisteis', 'redujeron'],
    subjunctive: ['reduzca', 'reduzcas', 'reduzca', 'reduzcamos', 'reduzcáis', 'reduzcan'],
  },
  reír: {
    present: ['río', 'ríes', 'ríe', 'reímos', 'reís', 'ríen'],
    preterite: ['reí', 'reíste', 'rió', 'reímos', 'reísteis', 'rieron'],
    subjunctive: ['ría', 'rías', 'ría', 'riamos', 'riais', 'rían'],
  },
  sonreír: {
    present: ['sonrío', 'sonríes', 'sonríe', 'sonreímos', 'sonreís', 'sonríen'],
    preterite: ['sonreí', 'sonreíste', 'sonrió', 'sonreímos', 'sonreísteis', 'sonrieron'],
    subjunctive: ['sonría', 'sonrías', 'sonría', 'sonriamos', 'sonriais', 'sonrían'],
  },
  freír: {
    present: ['frío', 'fríes', 'fríe', 'freímos', 'freís', 'fríen'],
    preterite: ['freí', 'freíste', 'frió', 'freímos', 'freísteis', 'frieron'],
    subjunctive: ['fría', 'frías', 'fría', 'friamos', 'friais', 'frían'],
  },
}

const BOOT = [0, 1, 2, 5] // persons that take the stem change in the present "boot"
const VOWELS = 'aeiouáéíóú'

// Verb group from the infinitive ending. Accented -ír (oír, reír, freír…)
// normalises to 'ir' so it lines up with the endings table.
function groupOf(infinitive: string): Group {
  const g = infinitive.slice(-2)
  return g === 'ar' || g === 'er' ? g : 'ir'
}

function changeStem(stem: string, type: string): string {
  const [from, to] = type.split('>')
  const i = stem.lastIndexOf(from)
  return i < 0 ? stem : stem.slice(0, i) + to + stem.slice(i + from.length)
}

function secondary(type: string): string {
  // -ir verbs take a weaker change outside the boot (preterite 3rd, subj nos/vos).
  if (type === 'e>ie') return 'e>i'
  if (type === 'o>ue') return 'o>u'
  return type // e>i stays e>i
}

// Adjust spelling so the stem's final consonant keeps its sound before the
// vowel that begins the ending. `back` = ending starts with o/a (hard side).
function spell(stem: string, group3: string, endingFirst: string): string {
  const front = 'eéií'.includes(endingFirst)
  const back = 'oaáó'.includes(endingFirst)
  if (group3 === 'car' && front) return stem.slice(0, -1) + 'qu'
  if (group3 === 'gar' && front) return stem + 'u'
  if (group3 === 'zar' && front) return stem.slice(0, -1) + 'c'
  if ((group3 === 'ger' || group3 === 'gir') && back) return stem.slice(0, -1) + 'j'
  if (group3 === 'uir' && stem.endsWith('gu') && back) return stem.slice(0, -1)
  if (group3 === 'cer' || group3 === 'cir') {
    if (back) {
      const before = stem[stem.length - 2]
      return VOWELS.includes(before) ? stem.slice(0, -1) + 'zc' : stem.slice(0, -1) + 'z'
    }
  }
  return stem
}

// True for -uir verbs that insert a 'y' (construir, incluir…) — but not -guir/-quir.
function isUir(infinitive: string): boolean {
  return infinitive.endsWith('uir') && !infinitive.endsWith('guir') && !infinitive.endsWith('quir')
}

// Reflexive proclitic pronouns (me levanto, te levantas…), indexed by person.
const REFLEX = ['me', 'te', 'se', 'nos', 'os', 'se']

function isReflexive(infinitive: string): boolean {
  return infinitive.endsWith('se') && infinitive.length > 3 && !(infinitive in IRREGULAR)
}

/** Conjugate one verb in one tense → six forms (yo..ellos). */
export function conjugate(infinitive: string, tense: Tense): Six {
  // Reflexive verbs: conjugate the base and prepend the reflexive pronoun.
  if (isReflexive(infinitive)) {
    const base = conjugate(infinitive.slice(0, -2), tense)
    return base.map((f, p) => `${REFLEX[p]} ${f}`) as Six
  }

  const irr = IRREGULAR[infinitive]?.[tense]
  if (irr) return irr

  const group = groupOf(infinitive)
  const group3 = infinitive.slice(-3)
  const raw = infinitive.slice(0, -2)
  const endings = REGULAR[tense][group]
  const stemType = STEM[infinitive]
  const uir = isUir(infinitive)
  const vowelStem = (group === 'er' || group === 'ir') && VOWELS.includes(raw[raw.length - 1]) && !uir

  // Future & conditional: one stem (irregular or the whole infinitive) + endings.
  if (tense === 'future' || tense === 'conditional') {
    const base = FUT_STEM[infinitive] ?? infinitive
    return endings.map((e) => base + e) as Six
  }

  return endings.map((ending, p) => {
    let stem = raw

    // 1. stem-vowel change
    if (stemType) {
      if (tense === 'present' && BOOT.includes(p)) {
        stem = changeStem(raw, stemType)
      } else if (tense === 'subjunctive') {
        stem = BOOT.includes(p)
          ? changeStem(raw, stemType)
          : group === 'ir'
            ? changeStem(raw, secondary(stemType))
            : raw
      } else if (tense === 'preterite' && group === 'ir' && (p === 2 || p === 5)) {
        stem = changeStem(raw, secondary(stemType))
      }
    }

    // 2. y-insertion for -uir verbs (present boot + all subjunctive + pret 3rd)
    if (uir) {
      if ((tense === 'present' && BOOT.includes(p)) || tense === 'subjunctive') stem += 'y'
    }

    // 3. preterite y / accent for vowel-stem -er/-ir (leer→leyó, caer pattern)
    let end = ending
    if (tense === 'preterite' && (vowelStem || uir)) {
      if (p === 2) end = end.replace(/^ió$/, 'yó')
      else if (p === 5) end = end.replace(/^ieron$/, 'yeron')
      else if (vowelStem && (p === 1 || p === 3 || p === 4)) end = 'í' + end.slice(1)
    }

    // 4. orthographic consonant spelling (skip when a y was just inserted)
    if (!(uir && (tense === 'subjunctive' || (tense === 'present' && BOOT.includes(p))))) {
      stem = spell(stem, group3, end[0])
    }

    return stem + end
  }) as Six
}

/** True if we have special handling (irregular or stem-changing) for this verb. */
export function isIrregular(infinitive: string): boolean {
  const base = isReflexive(infinitive) ? infinitive.slice(0, -2) : infinitive
  return base in IRREGULAR || base in STEM
}

export interface RichForm {
  pron: string | null // reflexive pronoun, or null
  stem: string // the part to render as the stem
  ending: string // the conjugation ending (highlighted)
  irregular: boolean // stem deviates from the plain infinitive stem
}

/**
 * Like `conjugate`, but splits each form into stem + ending so the UI can
 * highlight what changes, and flags forms whose stem is irregular/stem-changed.
 * Fully-irregular forms (soy, fui…) come back as a single irregular chunk.
 */
export function conjugateRich(infinitive: string, tense: Tense): RichForm[] {
  const six = conjugate(infinitive, tense)
  const reflexive = isReflexive(infinitive)
  const base = reflexive ? infinitive.slice(0, -2) : infinitive
  const group = groupOf(base)
  const rawStem = base.slice(0, -2)
  // Only treat as a single irregular chunk when THIS tense is explicitly
  // irregular — rule-computed tenses (e.g. tener's future) still split.
  const tenseIrr = !!IRREGULAR[base]?.[tense]
  const futLike = tense === 'future' || tense === 'conditional'
  const endings = REGULAR[tense][group]

  return six.map((full, p) => {
    let pron: string | null = null
    let word = full
    if (reflexive) {
      const i = full.indexOf(' ')
      pron = full.slice(0, i)
      word = full.slice(i + 1)
    }
    const end = endings[p]
    if (tenseIrr || !end || !word.endsWith(end)) {
      return { pron, stem: word, ending: '', irregular: true }
    }
    const stem = word.slice(0, word.length - end.length)
    const irregular = futLike ? base in FUT_STEM : stem !== rawStem
    return { pron, stem, ending: end, irregular }
  })
}
