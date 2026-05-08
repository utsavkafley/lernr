<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import api from '@/composables/useApi'

interface ConceptStat {
  concept_id: number
  name: string
  total_attempts: number
  correct_attempts: number
  accuracy: number
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
  const { data } = await api.get('/progress/summary')
  summary.value = data
  loading.value = false
})

const sortedConcepts = computed(() => {
  if (!summary.value) return []
  return [...summary.value.concept_stats]
    .filter(c => c.accuracy < 0.8)
    .sort((a, b) => a.accuracy - b.accuracy)
})

const trackPct = computed(() => {
  if (!summary.value || !summary.value.total_tracks) return 0
  return Math.round((summary.value.tracks_completed / summary.value.total_tracks) * 100)
})

const accuracyPct = computed(() =>
  summary.value ? Math.round(summary.value.overall_accuracy * 100) : 0,
)

function accuracyColor(accuracy: number) {
  if (accuracy >= 0.8) return 'text-emerald-600 dark:text-emerald-400'
  if (accuracy >= 0.5) return 'text-amber-600 dark:text-amber-400'
  return 'text-rose-600 dark:text-rose-400'
}

function accuracyBarColor(accuracy: number) {
  if (accuracy >= 0.8) return 'bg-emerald-500'
  if (accuracy >= 0.5) return 'bg-amber-500'
  return 'bg-rose-500'
}

function accuracyBg(accuracy: number) {
  if (accuracy >= 0.8) return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-300'
  if (accuracy >= 0.5) return 'bg-amber-100 text-amber-800 dark:bg-amber-950/50 dark:text-amber-300'
  return 'bg-rose-100 text-rose-800 dark:bg-rose-950/50 dark:text-rose-300'
}

function accuracyLabel(accuracy: number) {
  if (accuracy >= 0.8) return 'Mastered'
  if (accuracy >= 0.5) return 'Developing'
  return 'Needs work'
}
</script>

<template>
  <div class="animate-fade-up">
    <div class="mb-10">
      <p class="text-sm font-medium text-primary uppercase tracking-wider mb-2">Progress</p>
      <h1 class="text-4xl font-bold tracking-tight">How you're doing</h1>
    </div>

    <div v-if="loading" class="space-y-4">
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div v-for="i in 4" :key="i" class="h-28 rounded-2xl bg-muted animate-pulse" />
      </div>
      <div class="h-72 rounded-2xl bg-muted animate-pulse" />
    </div>

    <div v-else-if="summary" class="space-y-8">
      <!-- Hero stat cards -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div class="rounded-2xl border border-border/60 bg-card p-5 relative overflow-hidden">
          <div class="absolute -top-4 -right-4 w-20 h-20 rounded-full bg-primary/5"></div>
          <p class="text-xs text-muted-foreground uppercase tracking-wider font-medium">Tracks done</p>
          <p class="text-3xl font-bold mt-2 tabular-nums">
            {{ summary.tracks_completed }}<span class="text-muted-foreground text-lg font-normal">/{{ summary.total_tracks }}</span>
          </p>
          <div class="mt-3 h-1.5 bg-muted rounded-full overflow-hidden">
            <div class="h-full bg-gradient-to-r from-primary to-accent-foreground transition-all duration-700" :style="{ width: `${trackPct}%` }" />
          </div>
        </div>

        <div class="rounded-2xl border border-border/60 bg-card p-5 relative overflow-hidden">
          <div class="absolute -top-4 -right-4 w-20 h-20 rounded-full bg-accent/30"></div>
          <p class="text-xs text-muted-foreground uppercase tracking-wider font-medium">Accuracy</p>
          <p class="text-3xl font-bold mt-2 tabular-nums" :class="accuracyColor(summary.overall_accuracy)">
            {{ accuracyPct }}%
          </p>
          <p class="text-xs text-muted-foreground mt-3">across all attempts</p>
        </div>

        <div class="rounded-2xl border border-border/60 bg-card p-5">
          <p class="text-xs text-muted-foreground uppercase tracking-wider font-medium">Attempts</p>
          <p class="text-3xl font-bold mt-2 tabular-nums">{{ summary.total_attempts }}</p>
          <p class="text-xs text-muted-foreground mt-3">questions answered</p>
        </div>

        <div class="rounded-2xl border border-border/60 bg-card p-5">
          <p class="text-xs text-muted-foreground uppercase tracking-wider font-medium">Concepts</p>
          <p class="text-3xl font-bold mt-2 tabular-nums">{{ summary.concept_stats.length }}</p>
          <p class="text-xs text-muted-foreground mt-3">encountered so far</p>
        </div>
      </div>

      <!-- Concept breakdown -->
      <div class="rounded-2xl border border-border/60 bg-card overflow-hidden">
        <div class="px-6 py-5 border-b border-border/60">
          <h2 class="text-lg font-semibold">Needs work</h2>
          <p class="text-sm text-muted-foreground mt-0.5">Concepts below mastery threshold, sorted by weakest first</p>
        </div>

        <div v-if="sortedConcepts.length === 0" class="p-10 text-center">
          <p class="text-sm text-muted-foreground">
            Nothing here — you've mastered every concept you've practiced! 🎉
          </p>
        </div>

        <div v-else class="divide-y divide-border/40">
          <div
            v-for="(concept, idx) in sortedConcepts"
            :key="concept.concept_id"
            class="px-6 py-3.5 hover:bg-muted/30 transition-colors"
            :style="{ animationDelay: `${Math.min(idx * 20, 400)}ms` }"
          >
            <div class="flex items-center gap-3 mb-2">
              <span class="font-medium flex-1 truncate">{{ concept.name }}</span>
              <span
                class="text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded-full"
                :class="accuracyBg(concept.accuracy)"
              >
                {{ accuracyLabel(concept.accuracy) }}
              </span>
              <span :class="accuracyColor(concept.accuracy)" class="font-bold tabular-nums w-12 text-right">
                {{ Math.round(concept.accuracy * 100) }}%
              </span>
            </div>
            <div class="h-1.5 bg-muted rounded-full overflow-hidden">
              <div
                class="h-full transition-all duration-500"
                :class="accuracyBarColor(concept.accuracy)"
                :style="{ width: `${concept.accuracy * 100}%` }"
              />
            </div>
            <p class="text-xs text-muted-foreground mt-1.5 tabular-nums">
              {{ concept.correct_attempts }} / {{ concept.total_attempts }} correct
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
