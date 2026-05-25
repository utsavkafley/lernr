<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import api from '@/composables/useApi'
import chatIllustration from '@/assets/chat.svg'

const router = useRouter()
const auth = useAuthStore()

interface ConceptStat {
  concept_id: number
  name: string
  blended: number
  mastered: boolean
}

interface Summary {
  tracks_completed: number
  total_tracks: number
  total_attempts: number
  overall_accuracy: number
  concept_stats: ConceptStat[]
}

const summary = ref<Summary | null>(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const { data } = await api.get('/progress/summary')
    summary.value = data
  } catch {
    // new user — no progress yet
  } finally {
    loading.value = false
  }
})

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 12) return 'Buenos días'
  if (h < 18) return 'Buenas tardes'
  return 'Buenas noches'
})

const nextConcept = computed(() => {
  if (!summary.value) return null
  return summary.value.concept_stats
    .filter(c => !c.mastered)
    .sort((a, b) => b.blended - a.blended)[0] ?? null
})

const masteredCount = computed(() =>
  summary.value?.concept_stats.filter(c => c.mastered).length ?? 0
)

const actions = [
  {
    label: 'AI Tutor',
    description: 'Socratic sessions — your friend who speaks Spanish.',
    icon: '🧠',
    color: 'bg-primary/10',
    to: '/tutor',
  },
  {
    label: 'Practice',
    description: 'Quick-fire quiz on concepts from your completed tracks.',
    icon: '⚡',
    color: 'bg-emerald-500/10',
    to: '/practice',
  },
  {
    label: 'Tracks',
    description: 'Browse Language Transfer episodes and mark them done.',
    icon: '🎧',
    color: 'bg-blue-500/10',
    to: '/tracks',
  },
]
</script>

<template>
  <div class="animate-fade-up">
    <!-- Hero -->
    <div class="relative mb-12 overflow-hidden rounded-3xl border border-border/60 bg-card px-8 py-12 md:px-14">
      <!-- Decorative blobs -->
      <div class="pointer-events-none absolute -top-12 -right-12 h-64 w-64 rounded-full blur-3xl" style="background: oklch(0.72 0.19 52 / 0.18)" />
      <div class="pointer-events-none absolute -bottom-8 -left-8 h-48 w-48 rounded-full blur-2xl" style="background: oklch(0.85 0.12 65 / 0.35)" />

      <!-- Illustration -->
      <img
        :src="chatIllustration"
        alt=""
        aria-hidden="true"
        class="pointer-events-none absolute right-4 md:right-10 bottom-2 w-44 md:w-72 select-none opacity-90 animate-float hidden sm:block"
      />

      <div class="relative max-w-lg">
        <p class="text-base font-medium text-primary mb-2">{{ greeting }},</p>
        <h1 class="font-display text-5xl md:text-6xl leading-[1.05] mb-4">
          <span class="font-sans font-bold tracking-tight">{{ auth.user?.username ?? 'learner' }}</span><span class="text-gradient font-display italic">.</span>
        </h1>
        <p class="text-lg text-muted-foreground leading-relaxed">
          You're building Spanish fluency with Language Transfer. Keep going — it compounds.
        </p>

        <!-- Quick stats if we have data -->
        <div v-if="summary && summary.total_attempts > 0" class="mt-6 flex flex-wrap gap-3">
          <span class="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-3.5 py-1.5 text-sm font-medium text-primary">
            {{ summary.tracks_completed }} / {{ summary.total_tracks }} tracks
          </span>
          <span class="inline-flex items-center gap-1.5 rounded-full bg-muted px-3.5 py-1.5 text-sm font-medium">
            {{ Math.round(summary.overall_accuracy * 100) }}% accuracy
          </span>
          <span class="inline-flex items-center gap-1.5 rounded-full bg-muted px-3.5 py-1.5 text-sm font-medium">
            {{ masteredCount }} concepts mastered
          </span>
        </div>
      </div>
    </div>

    <!-- Continue where you left off -->
    <div
      v-if="nextConcept"
      class="mb-8 flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-2xl border border-primary/20 bg-primary/[0.03] px-6 py-5 animate-fade-up"
      style="animation-delay: 100ms"
    >
      <div>
        <p class="text-xs font-semibold uppercase tracking-widest text-primary mb-1">Continue where you left off</p>
        <p class="text-xl font-semibold">{{ nextConcept.name }}</p>
        <div class="mt-2 flex items-center gap-2">
          <div class="h-1.5 w-32 overflow-hidden rounded-full bg-primary/20">
            <div class="h-full rounded-full bg-primary transition-all" :style="{ width: `${nextConcept.blended * 100}%` }" />
          </div>
          <span class="text-xs text-muted-foreground">{{ Math.round(nextConcept.blended * 100) }}%</span>
        </div>
      </div>
      <div class="flex gap-2 shrink-0">
        <button
          @click="router.push({ path: '/tutor', query: { concept_id: nextConcept.concept_id, concept_name: nextConcept.name } })"
          class="rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground hover:opacity-90 transition-opacity"
        >Chat</button>
        <button
          @click="router.push({ path: '/practice', query: { concept_id: nextConcept.concept_id, concept_name: nextConcept.name } })"
          class="rounded-xl bg-muted px-5 py-2.5 text-sm font-semibold text-foreground hover:bg-muted/70 transition-colors"
        >Quiz</button>
      </div>
    </div>

    <!-- New user CTA (no attempts yet) -->
    <div
      v-else-if="!loading && (!summary || summary.total_attempts === 0)"
      class="mb-8 rounded-2xl border border-dashed border-border bg-card px-6 py-8 text-center animate-fade-up"
      style="animation-delay: 100ms"
    >
      <p class="text-4xl mb-3">🎧</p>
      <p class="font-semibold mb-1">Start with a track</p>
      <p class="text-sm text-muted-foreground mb-4">Listen to an episode, mark it complete, then come back to practice.</p>
      <button @click="router.push('/tracks')" class="rounded-xl bg-primary px-6 py-2.5 text-sm font-semibold text-primary-foreground hover:opacity-90 transition-opacity">
        Browse tracks →
      </button>
    </div>

    <!-- Quick actions -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <button
        v-for="(action, i) in actions"
        :key="action.to"
        @click="router.push(action.to)"
        class="group rounded-2xl border border-border/60 bg-card p-6 text-left transition-all hover:-translate-y-1 hover:shadow-xl hover:shadow-foreground/5 animate-fade-up"
        :style="{ animationDelay: `${(i + 2) * 80}ms` }"
      >
        <div
          class="mb-4 flex h-12 w-12 items-center justify-center rounded-xl text-2xl transition-transform group-hover:scale-110"
          :class="action.color"
        >{{ action.icon }}</div>
        <p class="mb-1 text-base font-semibold">{{ action.label }}</p>
        <p class="text-sm text-muted-foreground leading-relaxed">{{ action.description }}</p>
      </button>
    </div>
  </div>
</template>
