import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

export function useStream() {
  const messages = ref<{ role: 'user' | 'assistant'; content: string }[]>([])
  const isStreaming = ref(false)
  const sessionId = ref<string | null>(null)
  const currentConcept = ref<string>('')

  const auth = useAuthStore()
  const BASE_URL = import.meta.env.VITE_API_URL

  async function send(userMessage: string) {
    if (!userMessage.trim() || isStreaming.value) return

    messages.value.push({ role: 'user', content: userMessage })
    isStreaming.value = true

    let assistantContent = ''
    messages.value.push({ role: 'assistant', content: '' })
    const assistantIndex = messages.value.length - 1

    try {
      const response = await fetch(`${BASE_URL}/agent/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${auth.token}`,
        },
        body: JSON.stringify({
          message: userMessage,
          session_id: sessionId.value,
        }),
      })

      const reader = response.body!.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const data = JSON.parse(line.slice(6))

          if (data.type === 'session') {
            sessionId.value = data.session_id
          } else if (data.type === 'token') {
            assistantContent += data.content
            messages.value[assistantIndex].content = assistantContent
          } else if (data.type === 'done') {
            currentConcept.value = data.concept
          }
        }
      }
    } finally {
      isStreaming.value = false
    }
  }

  async function startSession() {
    isStreaming.value = true
    let assistantContent = ''
    messages.value.push({ role: 'assistant', content: '' })
    const assistantIndex = messages.value.length - 1

    try {
      const response = await fetch(`${BASE_URL}/agent/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${auth.token}`,
        },
        body: JSON.stringify({ session_id: null }),
      })

      const reader = response.body!.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const data = JSON.parse(line.slice(6))

          if (data.type === 'session') {
            sessionId.value = data.session_id
          } else if (data.type === 'token') {
            assistantContent += data.content
            messages.value[assistantIndex].content = assistantContent
          } else if (data.type === 'done') {
            currentConcept.value = data.concept
          }
        }
      }
    } finally {
      isStreaming.value = false
    }
  }

  return { messages, isStreaming, sessionId, currentConcept, send, startSession }
}
