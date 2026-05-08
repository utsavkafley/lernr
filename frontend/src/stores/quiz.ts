import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/composables/useApi'

interface Concept {
  id: number
  name: string
}

interface Question {
  question_id: number
  prompt: string
  concepts: Concept[]
}

interface SubmitResult {
  evaluation_state: 'correct' | 'acceptable' | 'incorrect'
  feedback: string
  expected_answer: string
  alternate_answers: string[]
}

export const useQuizStore = defineStore('quiz', () => {
  const question = ref<Question | null>(null)
  const result = ref<SubmitResult | null>(null)
  const hint = ref<string | null>(null)
  const loading = ref(false)
  const noTracksCompleted = ref(false)

  // Session stats
  const sessionTotal = ref(0)
  const sessionCorrect = ref(0)

  async function fetchNext() {
    loading.value = true
    result.value = null
    hint.value = null
    noTracksCompleted.value = false
    try {
      const { data } = await api.get('/quiz/next')
      question.value = data
    } catch (err: any) {
      if (err.response?.status === 404) {
        noTracksCompleted.value = true
        question.value = null
      }
    } finally {
      loading.value = false
    }
  }

  async function fetchHint() {
    if (!question.value) return
    const { data } = await api.get(`/quiz/hint/${question.value.question_id}`)
    hint.value = data.hint
  }

  async function submitAnswer(userAnswer: string) {
    if (!question.value) return
    const { data } = await api.post('/quiz/submit', {
      question_id: question.value.question_id,
      user_answer: userAnswer,
    })
    result.value = data
    sessionTotal.value++
    if (data.evaluation_state !== 'incorrect') {
      sessionCorrect.value++
    }
  }

  function resetSession() {
    question.value = null
    result.value = null
    hint.value = null
    sessionTotal.value = 0
    sessionCorrect.value = 0
    noTracksCompleted.value = false
  }

  return {
    question,
    result,
    hint,
    loading,
    noTracksCompleted,
    sessionTotal,
    sessionCorrect,
    fetchNext,
    fetchHint,
    submitAnswer,
    resetSession,
  }
})
