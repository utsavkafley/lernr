import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/composables/useApi'

export interface Track {
  id: number
  number: number
  title: string
  description: string | null
  completed: boolean
}

export const useTracksStore = defineStore('tracks', () => {
  const tracks = ref<Track[]>([])
  const loading = ref(false)

  async function fetchTracks() {
    loading.value = true
    try {
      const { data } = await api.get('/tracks')
      tracks.value = data
    } finally {
      loading.value = false
    }
  }

  async function markComplete(number: number) {
    await api.post(`/progress/tracks/${number}/complete`)
    const track = tracks.value.find((t) => t.number === number)
    if (track) track.completed = true
  }

  async function unmarkComplete(number: number) {
    await api.delete(`/progress/tracks/${number}/complete`)
    const track = tracks.value.find((t) => t.number === number)
    if (track) track.completed = false
  }

  const completedCount = () => tracks.value.filter((t) => t.completed).length

  return { tracks, loading, fetchTracks, markComplete, unmarkComplete, completedCount }
})
