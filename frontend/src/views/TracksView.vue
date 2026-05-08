<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useTracksStore } from '@/stores/tracks'
import { usePlayerStore } from '@/stores/player'

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
    <div v-if="store.loading" class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
      <div
        v-for="i in 12"
        :key="i"
        class="h-16 rounded-xl bg-muted animate-pulse"
      />
    </div>

    <!-- Track list -->
    <div v-else class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
      <div
        v-for="(track, idx) in store.tracks"
        :key="track.id"
        class="group flex items-center gap-3 px-4 py-3 rounded-xl border bg-card transition-all hover:shadow-md hover:shadow-foreground/5 hover:-translate-y-0.5 animate-fade-up"
        :class="[
          track.completed ? 'border-primary/20 bg-primary/[0.03]' : 'border-border/70',
          player.activeTrackNumber === track.number ? 'ring-2 ring-primary/30 shadow-md' : '',
        ]"
        :style="{ animationDelay: `${Math.min(idx * 15, 300)}ms` }"
      >
        <!-- Track number -->
        <div
          class="w-10 h-10 rounded-lg flex items-center justify-center shrink-0 text-sm font-bold tabular-nums transition-colors"
          :class="track.completed
            ? 'bg-primary/10 text-primary'
            : 'bg-muted text-muted-foreground'"
        >
          {{ track.number }}
        </div>

        <!-- Title -->
        <div class="min-w-0 flex-1">
          <p
            class="text-sm font-semibold truncate leading-tight"
            :class="track.completed ? 'text-foreground' : 'text-foreground'"
          >
            {{ track.title }}
          </p>
          <p v-if="track.description" class="text-xs text-muted-foreground truncate mt-0.5">
            {{ track.description }}
          </p>
        </div>

        <!-- Play button -->
        <button
          @click="player.play(track.number, track.title)"
          class="w-9 h-9 rounded-full flex items-center justify-center shrink-0 transition-all opacity-60 group-hover:opacity-100 hover:bg-primary hover:text-primary-foreground hover:scale-110"
          :class="player.activeTrackNumber === track.number
            ? 'bg-primary text-primary-foreground opacity-100'
            : 'bg-muted text-foreground'"
          :aria-label="`Play ${track.title}`"
        >
          <svg class="w-3.5 h-3.5 ml-0.5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M8 5v14l11-7z" />
          </svg>
        </button>

        <!-- Completion toggle -->
        <button
          @click="toggle(track.number, track.completed)"
          class="w-7 h-7 rounded-full border-2 flex items-center justify-center shrink-0 transition-all hover:scale-110"
          :class="track.completed
            ? 'border-primary bg-primary'
            : 'border-muted-foreground/40 hover:border-primary'"
          :aria-label="track.completed ? 'Mark incomplete' : 'Mark complete'"
        >
          <svg
            v-if="track.completed"
            class="w-3.5 h-3.5 text-primary-foreground"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="3"
          >
            <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>
