import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export function useStream() {
  const messages = ref<ChatMessage[]>([])
  const isStreaming = ref(false)
  const sessionId = ref<string | null>(null)
  const currentConcept = ref<string>('')
  const lastEvaluation = ref<string>('')
  const currentStep = ref(0)
  const totalSteps = ref(0)

  const auth = useAuthStore()
  const BASE_URL = import.meta.env.VITE_API_URL

  async function _callAgent(payload: { message?: string; session_id?: string | null }) {
    const response = await fetch(`${BASE_URL}/agent/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${auth.token}`,
      },
      body: JSON.stringify(payload),
    })

    if (!response.ok) throw new Error(`Agent error: ${response.status}`)

    const reader = response.body!.getReader()
    const decoder = new TextDecoder()
    let assistantContent = ''
    let assistantIndex = -1

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const chunk = decoder.decode(value)
      for (const line of chunk.split('\n')) {
        if (!line.startsWith('data: ')) continue
        let data: Record<string, string>
        try {
          data = JSON.parse(line.slice(6))
        } catch {
          continue
        }

        if (data.type === 'session') {
          sessionId.value = data.session_id
        } else if (data.type === 'token') {
          if (assistantIndex === -1) {
            messages.value.push({ role: 'assistant', content: '' })
            assistantIndex = messages.value.length - 1
            assistantContent = ''
          }
          assistantContent += data.content
          messages.value[assistantIndex].content = assistantContent
        } else if (data.type === 'done') {
          currentConcept.value = data.concept ?? ''
          lastEvaluation.value = data.evaluation ?? ''
          currentStep.value = Number(data.step ?? 0)
          totalSteps.value = Number(data.total_steps ?? 0)
        }
      }
    }
  }

  /** Start a fresh session — AI asks the first question. */
  async function startSession() {
    if (isStreaming.value) return
    isStreaming.value = true
    try {
      await _callAgent({ session_id: null })
    } finally {
      isStreaming.value = false
    }
  }

  /** Send a user message and stream the AI response. */
  async function send(userMessage: string) {
    if (!userMessage.trim() || isStreaming.value) return
    messages.value.push({ role: 'user', content: userMessage.trim() })
    isStreaming.value = true
    try {
      await _callAgent({ message: userMessage.trim(), session_id: sessionId.value })
    } finally {
      isStreaming.value = false
    }
  }

  function reset() {
    messages.value = []
    sessionId.value = null
    currentConcept.value = ''
    lastEvaluation.value = ''
    currentStep.value = 0
    totalSteps.value = 0
  }

  return { messages, isStreaming, sessionId, currentConcept, lastEvaluation, currentStep, totalSteps, send, startSession, reset }
}
