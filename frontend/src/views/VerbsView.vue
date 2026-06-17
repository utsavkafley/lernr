<script setup lang="ts">
import { ref, computed } from 'vue'
import { Volume2 } from 'lucide-vue-next'
import { TIERS, ALL_VERBS } from '@/data/verbs'
import {
  conjugateRich,
  isIrregular,
  TENSES,
  PERSONS,
  type Tense,
  type RichForm,
} from '@/lib/conjugate'
import { speakSpanish } from '@/composables/useSpeech'

const activeTier = ref(0)
const person = ref(0) // index into PERSONS
const tense = ref<Tense>('present')
const search = ref('')
const pinned = ref<Set<string>>(new Set()) // verbs flipped open by click (touch-friendly)

const tier = computed(() => TIERS[activeTier.value])

const visibleVerbs = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return tier.value.verbs
  // When searching, look across every tier so nothing is hidden.
  return ALL_VERBS.filter(
    (v) => v.es.includes(q) || v.en.toLowerCase().includes(q),
  )
})

// One conjugated, stem/ending-split entry per visible verb for the current
// pairing + tense. Recomputes whenever the radios change.
const cards = computed(() =>
  visibleVerbs.value.map((v) => ({
    es: v.es,
    en: v.en,
    irr: isIrregular(v.es),
    rich: conjugateRich(v.es, tense.value)[person.value],
  })),
)

const personMeta = computed(() => PERSONS[person.value])
const tenseMeta = computed(() => TENSES.find((t) => t.id === tense.value)!)

function fullForm(r: RichForm): string {
  return `${r.pron ? r.pron + ' ' : ''}${r.stem}${r.ending}`
}

function speak(r: RichForm) {
  speakSpanish(fullForm(r))
}

// English hint for a tense, conjugated to match the selected pairing —
// e.g. tú + Preterite → "You saw", él/ella + Present → "He / she sees".
function tenseHint(t: Tense): string {
  const subj = PERSONS[person.value].english
  const is3sg = person.value === 2
  const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1)
  switch (t) {
    case 'present': return cap(`${subj} ${is3sg ? 'sees' : 'see'}`)
    case 'preterite': return cap(`${subj} saw`)
    case 'imperfect': return cap(`${subj} used to see`)
    case 'future': return cap(`${subj} will see`)
    case 'conditional': return cap(`${subj} would see`)
    case 'subjunctive': return `…that ${subj} see`
  }
}

function togglePin(es: string) {
  const next = new Set(pinned.value)
  next.has(es) ? next.delete(es) : next.add(es)
  pinned.value = next
}
</script>

<template>
  <div class="animate-fade-up">
    <!-- Header -->
    <div class="mb-8">
      <p class="text-xs font-semibold uppercase tracking-widest text-primary mb-2">Verb explorer</p>
      <h1 class="font-display text-4xl md:text-5xl leading-[1.05] mb-3">
        {{ ALL_VERBS.length }} essential verbs<span class="text-gradient font-display italic">.</span>
      </h1>
      <p class="text-muted-foreground max-w-2xl leading-relaxed">
        Hover a card to flip from English to Spanish. Pick a subject and tense on the left
        and every verb conjugates live — the <span class="text-primary font-medium">ending</span>
        is highlighted, an <span class="text-amber-600 dark:text-amber-400 font-medium">amber stem</span>
        marks an irregular change, and the speaker reads it aloud.
      </p>
    </div>

    <!-- Tier tabs -->
    <div class="flex flex-wrap gap-2 mb-6">
      <button
        v-for="(t, i) in TIERS"
        :key="t.title"
        @click="activeTier = i; search = ''"
        class="rounded-full px-4 py-1.5 text-sm font-medium transition-all"
        :class="i === activeTier && !search
          ? 'bg-foreground text-background'
          : 'bg-muted text-muted-foreground hover:text-foreground'"
      >
        Tier {{ i + 1 }}
      </button>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-[220px_1fr] gap-8">
      <!-- Controls -->
      <aside class="lg:sticky lg:top-24 self-start space-y-6">
        <!-- Search -->
        <input
          v-model="search"
          type="text"
          placeholder="Search verbs…"
          class="w-full rounded-xl border border-border/60 bg-card px-3.5 py-2 text-sm outline-none focus:border-primary/60 transition-colors"
        />

        <!-- Pairing (subject pronoun) -->
        <fieldset>
          <legend class="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-2.5">
            Pairing
          </legend>
          <div class="space-y-1">
            <label
              v-for="p in PERSONS"
              :key="p.id"
              class="flex items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-sm cursor-pointer transition-colors"
              :class="person === p.id ? 'bg-primary/10 text-primary font-medium' : 'hover:bg-muted'"
            >
              <input type="radio" name="person" :value="p.id" v-model="person" class="accent-primary" />
              <span>{{ p.pronoun }}</span>
              <span class="ml-auto text-xs text-muted-foreground">{{ p.english }}</span>
            </label>
          </div>
        </fieldset>

        <!-- Tense -->
        <fieldset>
          <legend class="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-2.5">
            Tense
          </legend>
          <div class="space-y-1">
            <label
              v-for="t in TENSES"
              :key="t.id"
              class="flex items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-sm cursor-pointer transition-colors"
              :class="tense === t.id ? 'bg-primary/10 text-primary font-medium' : 'hover:bg-muted'"
            >
              <input type="radio" name="tense" :value="t.id" v-model="tense" class="accent-primary" />
              <span>{{ t.label }}</span>
              <span class="ml-auto text-xs text-muted-foreground italic">{{ tenseHint(t.id) }}</span>
            </label>
          </div>
        </fieldset>
      </aside>

      <!-- Verb grid -->
      <section>
        <div v-if="!search" class="mb-5">
          <h2 class="text-xl font-semibold">{{ tier.title }}</h2>
          <p class="text-sm text-muted-foreground">{{ tier.subtitle }}</p>
        </div>
        <p v-else class="mb-5 text-sm text-muted-foreground">
          {{ visibleVerbs.length }} match{{ visibleVerbs.length === 1 ? '' : 'es' }} for “{{ search }}”
        </p>

        <div class="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-4 gap-3">
          <div
            v-for="c in cards"
            :key="c.es"
            class="flip-card"
            :class="{ 'is-flipped': pinned.has(c.es) }"
            @click="togglePin(c.es)"
            role="button"
            tabindex="0"
            @keydown.enter.prevent="togglePin(c.es)"
            @keydown.space.prevent="togglePin(c.es)"
          >
            <div class="flip-inner rounded-2xl">
              <!-- Front: English -->
              <div class="flip-face rounded-2xl border border-border/60 bg-card px-3 py-4 flex flex-col items-center justify-center text-center">
                <span class="text-sm font-medium leading-snug">{{ c.en }}</span>
                <span class="mt-2 text-[10px] uppercase tracking-widest text-muted-foreground/70">flip</span>
              </div>

              <!-- Back: conjugated Spanish, stem/ending colour-coded -->
              <div class="flip-face flip-back rounded-2xl border border-primary/30 bg-primary/[0.06] px-3 py-4 flex flex-col items-center justify-center text-center">
                <!-- Speaker -->
                <button
                  @click.stop="speak(c.rich)"
                  class="absolute top-1.5 right-1.5 p-1 rounded-md text-muted-foreground/70 hover:text-primary hover:bg-primary/10 transition-colors"
                  title="Hear it"
                  aria-label="Hear pronunciation"
                >
                  <Volume2 class="w-4 h-4" />
                </button>

                <span class="text-[11px] text-muted-foreground">{{ personMeta.pronoun }}</span>
                <span class="text-lg font-semibold leading-tight">
                  <span v-if="c.rich.pron" class="font-normal text-muted-foreground">{{ c.rich.pron }} </span><span :class="c.rich.irregular ? 'text-amber-600 dark:text-amber-400' : 'text-foreground'">{{ c.rich.stem }}</span><span class="text-primary">{{ c.rich.ending }}</span>
                </span>
                <span class="mt-1.5 text-[10px] uppercase tracking-widest text-muted-foreground/70">
                  {{ c.es }}
                  <span v-if="c.irr" title="irregular / stem-changing">★</span>
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- Legend -->
        <div class="mt-6 flex flex-wrap items-center gap-x-5 gap-y-1.5 text-xs text-muted-foreground">
          <span class="flex items-center gap-1.5"><span class="text-primary font-semibold">-o</span> ending</span>
          <span class="flex items-center gap-1.5"><span class="text-amber-600 dark:text-amber-400 font-semibold">stem</span> irregular change</span>
          <span class="flex items-center gap-1.5"><span class="text-primary">★</span> irregular / stem-changing verb</span>
          <span class="flex items-center gap-1.5"><Volume2 class="w-3.5 h-3.5" /> hear it</span>
          <span class="ml-auto">
            Showing <span class="font-medium text-foreground">{{ tenseMeta.label.toLowerCase() }}</span>,
            <span class="font-medium text-foreground">{{ personMeta.pronoun }}</span>
          </span>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.flip-card {
  perspective: 800px;
  cursor: pointer;
  outline: none;
  aspect-ratio: 5 / 4;
}
.flip-inner {
  position: relative;
  width: 100%;
  height: 100%;
  transform-style: preserve-3d;
  transition: transform 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}
.flip-card:hover .flip-inner,
.flip-card:focus-visible .flip-inner,
.flip-card.is-flipped .flip-inner {
  transform: rotateY(180deg);
}
.flip-face {
  position: absolute;
  inset: 0;
  backface-visibility: hidden;
  -webkit-backface-visibility: hidden;
  /* Explicit rotateY(0) keeps the front face in 3D space so the browser
     culls it correctly once the card flips (otherwise it shows mirrored). */
  transform: rotateY(0deg);
}
.flip-back {
  transform: rotateY(180deg);
}
.flip-card:focus-visible .flip-inner {
  box-shadow: 0 0 0 2px var(--primary);
  border-radius: 1rem;
}
</style>
