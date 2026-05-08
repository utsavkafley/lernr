<script setup lang="ts">
import { computed } from 'vue'
import { usePlayerStore } from '@/stores/player'
import { Button } from '@/components/ui/button'

const player = usePlayerStore()

function trackUrl(n: number): string {
  return `https://soundcloud.com/languagetransfer/complete-spanish-track-${n}-language-transfer-the-thinking-method`
}

const embedUrl = computed(() => {
  if (player.activeTrackNumber === null) return ''
  const params = new URLSearchParams({
    url: trackUrl(player.activeTrackNumber),
    auto_play: 'true',
    show_comments: 'false',
    show_user: 'false',
    show_reposts: 'false',
    show_teaser: 'false',
    visual: 'false',
  })
  return `https://w.soundcloud.com/player/?${params.toString()}`
})
</script>

<template>
  <div
    v-if="player.activeTrackNumber !== null"
    class="fixed bottom-0 left-0 right-0 bg-background border-t border-border shadow-lg z-20"
  >
    <div class="max-w-4xl mx-auto px-6 py-3">
      <div class="flex items-center justify-between mb-2">
        <p class="text-sm font-medium truncate">
          <span class="text-muted-foreground">Now playing:</span> {{ player.activeTrackTitle }}
        </p>
        <Button variant="ghost" size="sm" @click="player.stop" class="shrink-0">✕</Button>
      </div>
      <iframe
        :key="player.activeTrackNumber"
        :src="embedUrl"
        width="100%"
        height="120"
        scrolling="no"
        frameborder="no"
        allow="autoplay"
        class="rounded"
      />
    </div>
  </div>
</template>
