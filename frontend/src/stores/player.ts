import { defineStore } from 'pinia'
import { ref } from 'vue'

export const usePlayerStore = defineStore('player', () => {
  const activeTrackNumber = ref<number | null>(null)
  const activeTrackTitle = ref<string>('')

  function play(trackNumber: number, title: string) {
    activeTrackNumber.value = trackNumber
    activeTrackTitle.value = title
  }

  function stop() {
    activeTrackNumber.value = null
    activeTrackTitle.value = ''
  }

  return { activeTrackNumber, activeTrackTitle, play, stop }
})
