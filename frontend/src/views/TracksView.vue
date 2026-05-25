<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useTracksStore } from '@/stores/tracks'
import { usePlayerStore } from '@/stores/player'
import type { Track } from '@/stores/tracks'

const store = useTracksStore()
const player = usePlayerStore()

onMounted(() => {
  store.fetchTracks()
})

async function toggle(number: number, completed: boolean) {
  if (completed) {
    await store.unmarkComplete(number)
  } else {
    await store.markComplete(number)
  }
}

const completionPct = computed(() => {
  if (!store.tracks.length) return 0
  return Math.round((store.completedCount() / store.tracks.length) * 100)
})

interface TrackGroup {
  label: string
  description: string
  emoji: string
  color: string
  tracks: Track[]
  completedCount: number
}

const GROUPS = [
  { label: 'Foundations', description: 'Core verbs, pronouns & basic sentence structure', emoji: '🌱', color: 'emerald', min: 1, max: 10 },
  { label: 'Connections', description: 'Object pronouns, irregular verbs & expanding vocabulary', emoji: '🔗', color: 'blue', min: 11, max: 20 },
  { label: 'Fluency', description: 'Past tense, reflexive verbs & complex sentences', emoji: '🌊', color: 'violet', min: 21, max: 30 },
  { label: 'Mastery', description: 'Subjunctive, nuanced expression & native patterns', emoji: '⭐', color: 'amber', min: 31, max: 99 },
]

const groupColorMap: Record<string, string> = {
  emerald: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-900/40',
  blue: 'bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-200 dark:border-blue-900/40',
  violet: 'bg-violet-500/10 text-violet-700 dark:text-violet-400 border-violet-200 dark:border-violet-900/40',
  amber: 'bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-200 dark:border-amber-900/40',
}

const trackGroups = computed<TrackGroup[]>(() => {
  return GROUPS.map(g => {
    const tracks = store.tracks.filter(t => t.number >= g.min && t.number <= g.max)
    return {
      label: g.label,
      description: g.description,
      emoji: g.emoji,
      color: g.color,
      tracks,
      completedCount: tracks.filter(t => t.completed).length,
    }
  }).filter(g => g.tracks.length > 0)
})
</script>

<template>
  <div class="animate-fade-up">
    <!-- Hero header -->
    <div class="mb-10">
      <p class="text-sm font-medium text-primary uppercase tracking-wider mb-2">Complete Spanish</p>
      <h1 class="text-4xl font-bold tracking-tight mb-3">Your tracks</h1>
      <p class="text-muted-foreground max-w-xl">
        Listen to a track, then mark it complete to unlock its questions in practice mode.
      </p>

      <!-- Progress bar -->
      <div v-if="!store.loading" class="mt-6 max-w-md">
        <div class="flex items-baseline justify-between mb-2">
          <span class="text-sm font-medium">
            {{ store.completedCount() }} of {{ store.tracks.length }} completed
          </span>
          <span class="text-2xl font-bold tabular-nums">{{ completionPct }}%</span>
        </div>
        <div class="h-2 bg-muted rounded-full overflow-hidden">
          <div
            class="h-full bg-gradient-to-r from-primary to-accent-foreground transition-all duration-700 ease-out"
            :style="{ width: `${completionPct}%` }"
          />
        </div>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="store.loading" class="space-y-6">
      <div v-for="i in 4" :key="i" class="space-y-2">
        <div class="h-8 w-40 rounded-lg bg-muted animate-pulse" />
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <div v-for="j in 4" :key="j" class="h-16 rounded-xl bg-muted animate-pulse" />
        </div>
      </div>
    </div>

    <!-- Grouped track list -->
    <div v-else class="space-y-8">
      <div
        v-for="(group, gi) in trackGroups"
        :key="group.label"
        class="animate-fade-up"
        :style="{ animationDelay: `${gi * 80}ms` }"
      >
        <!-- Group header -->
        <div class="flex items-center gap-3 mb-3">
          <span
            class="inline-flex items-center gap-2 rounded-xl border px-3.5 py-1.5 text-sm font-semibold"
            :class="groupColorMap[group.color]"
          >
            {{ group.emoji }} {{ group.label }}
          </span>
          <span class="text-xs text-muted-foreground">
            {{ group.description }}
          </span>
          <span class="ml-auto text-xs font-medium tabular-nums text-muted-foreground shrink-0">
            {{ group.completedCount }}/{{ group.tracks.length }}
          </span>
        </div>

        <!-- Tracks in group -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <div
            v-for="track in group.tracks"
            :key="track.id"
            class="group flex items-center gap-3 px-4 py-3 rounded-xl border bg-card transition-all hover:shadow-md hover:shadow-foreground/5 hover:-translate-y-0.5"
            :class="[
              track.completed ? 'border-primary/20 bg-primary/[0.03]' : 'border-border/70',
              player.activeTrackNumber === track.number ? 'ring-2 ring-primary/30 shadow-md' : '',
            ]"
          >
            <!-- Track number -->
            <div
              class="w-9 h-9 rounded-lg flex items-center justify-center shrink-0 text-xs font-bold tabular-nums transition-colors"
              :class="track.completed ? 'bg-primary/10 text-primary' : 'bg-muted text-muted-foreground'"
            >{{ track.number }}</div>

            <!-- Title -->
            <div class="min-w-0 flex-1">
              <p class="text-sm font-semibold truncate leading-tight">{{ track.title }}</p>
              <p v-if="track.description" class="text-xs text-muted-foreground truncate mt-0.5">{{ track.description }}</p>
            </div>

            <!-- Play button -->
            <button
              @click="player.play(track.number, track.title)"
              class="w-8 h-8 rounded-full flex items-center justify-center shrink-0 transition-all opacity-50 group-hover:opacity-100 hover:bg-primary hover:text-primary-foreground hover:scale-110"
              :class="player.activeTrackNumber === track.number ? 'bg-primary text-primary-foreground opacity-100' : 'bg-muted text-foreground'"
              :aria-label="`Play ${track.title}`"
            >
              <svg class="w-3 h-3 ml-0.5" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
            </button>

            <!-- Completion toggle -->
            <button
              @click="toggle(track.number, track.completed)"
              class="w-6 h-6 rounded-full border-2 flex items-center justify-center shrink-0 transition-all hover:scale-110"
              :class="track.completed ? 'border-primary bg-primary' : 'border-muted-foreground/40 hover:border-primary'"
              :aria-label="track.completed ? 'Mark incomplete' : 'Mark complete'"
            >
              <svg v-if="track.completed" class="w-3 h-3 text-primary-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
