<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useQuizStore } from '@/stores/quiz'

const route = useRoute()
import { speakSpanish } from '@/composables/useSpeech'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import tutorIllustration from '@/assets/tutor_question.svg'

const quiz = useQuizStore()
const answer = ref('')
const inputEl = ref<InstanceType<typeof Input> | null>(null)
// Snapshot the answer at submit time so it survives clearing the input.
const submittedAnswer = ref('')

watch(
  () => quiz.result,
  (result) => {
    if (result) speakSpanish(result.expected_answer)
  },
)

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && quiz.result) {
    next()
  }
}

onMounted(() => {
  const conceptId = route.query.concept_id ? Number(route.query.concept_id) : null
  quiz.resetSession(conceptId)
  quiz.fetchNext()
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})

async function submit() {
  if (!answer.value.trim()) return
  submittedAnswer.value = answer.value.trim()
  await quiz.submitAnswer(submittedAnswer.value)
}

async function next() {
  answer.value = ''
  submittedAnswer.value = ''
  await quiz.fetchNext()
  nextTick(() => inputEl.value?.$el?.focus())
}

function dismissMastery() {
  quiz.clearNewlyMastered()
}

const accuracy = computed(() =>
  quiz.sessionTotal > 0 ? Math.round((quiz.sessionCorrect / quiz.sessionTotal) * 100) : 0,
)

interface ResultStyle {
  bg: string
  border: string
  text: string
  accent: string
  icon: string
  label: string
}

const stateConfig: Record<'correct' | 'acceptable' | 'incorrect', ResultStyle> = {
  correct: {
    bg: 'bg-emerald-50 dark:bg-emerald-950/40',
    border: 'border-emerald-200 dark:border-emerald-900',
    text: 'text-emerald-900 dark:text-emerald-100',
    accent: 'text-emerald-600 dark:text-emerald-400',
    icon: '✓',
    label: 'Correct',
  },
  acceptable: {
    bg: 'bg-amber-50 dark:bg-amber-950/40',
    border: 'border-amber-200 dark:border-amber-900',
    text: 'text-amber-900 dark:text-amber-100',
    accent: 'text-amber-600 dark:text-amber-400',
    icon: '~',
    label: 'Close',
  },
  incorrect: {
    bg: 'bg-rose-50 dark:bg-rose-950/40',
    border: 'border-rose-200 dark:border-rose-900',
    text: 'text-rose-900 dark:text-rose-100',
    accent: 'text-rose-600 dark:text-rose-400',
    icon: '×',
    label: 'Not quite',
  },
}
</script>

<template>
  <div class="max-w-2xl mx-auto">
    <!-- Header -->
    <div class="flex items-end justify-between mb-8 animate-fade-up">
      <div>
        <p class="text-sm font-medium text-primary uppercase tracking-wider mb-2">Practice</p>
        <h1 class="text-4xl font-bold tracking-tight">
          Build your fluency
        </h1>
        <p v-if="route.query.concept_name" class="text-sm text-muted-foreground mt-1">
          Focused on: <span class="font-medium text-foreground">{{ route.query.concept_name }}</span>
        </p>
      </div>
      <div v-if="quiz.sessionTotal > 0" class="text-right">
        <p class="text-3xl font-bold tabular-nums">{{ accuracy }}%</p>
        <p class="text-xs text-muted-foreground">
          {{ quiz.sessionCorrect }} / {{ quiz.sessionTotal }} this session
        </p>
      </div>
    </div>

    <!-- No completed tracks -->
    <div v-if="quiz.noTracksCompleted" class="border border-border/60 rounded-2xl p-10 text-center bg-card animate-scale-in">
      <img :src="tutorIllustration" alt="" aria-hidden="true" class="w-44 mx-auto mb-5 animate-float" />
      <p class="text-lg font-semibold mb-1">No completed tracks yet</p>
      <p class="text-sm text-muted-foreground max-w-sm mx-auto">
        Listen to your first Language Transfer track, then mark it complete on the Tracks page to unlock practice questions.
      </p>
    </div>

    <!-- Loading -->
    <div v-else-if="quiz.loading" class="space-y-4">
      <div class="h-48 rounded-2xl bg-muted animate-pulse" />
    </div>

    <!-- Question -->
    <div v-else-if="quiz.question" :key="quiz.question.question_id" class="animate-scale-in">
      <!-- Question card -->
      <div class="bg-card border border-border/60 rounded-2xl p-8 shadow-xl shadow-foreground/[0.04]">
        <div class="flex flex-wrap gap-1.5 mb-5">
          <Badge
            v-for="concept in quiz.question.concepts"
            :key="concept.id"
            variant="secondary"
            class="text-xs font-medium"
          >
            {{ concept.name }}
          </Badge>
        </div>
        <h2 class="text-2xl font-semibold leading-snug tracking-tight mb-6">
          {{ quiz.question.prompt }}
        </h2>

        <!-- Answer input -->
        <div v-if="!quiz.result" class="space-y-3">
          <div class="flex gap-2">
            <Input
              ref="inputEl"
              v-model="answer"
              placeholder="Type your Spanish answer…"
              @keydown.enter="submit"
              autofocus
              class="h-12 text-base"
            />
            <Button @click="submit" :disabled="!answer.trim()" class="h-12 px-6 font-medium">
              Submit
            </Button>
          </div>

          <!-- Hint -->
          <div class="flex items-center gap-3 min-h-9">
            <Button
              v-if="!quiz.hint"
              @click="quiz.fetchHint"
              variant="ghost"
              size="sm"
              class="text-muted-foreground hover:text-foreground -ml-2"
            >
              💡 Need a hint?
            </Button>
            <p
              v-else
              class="text-base font-mono tracking-[0.2em] px-4 py-2 rounded-lg bg-muted text-foreground animate-fade-up"
            >
              {{ quiz.hint }}
            </p>
          </div>
        </div>

        <!-- Result -->
        <div v-if="quiz.result" class="space-y-4 animate-fade-up">
          <!-- Status banner -->
          <div
            class="rounded-xl px-5 py-4 border"
            :class="[
              stateConfig[quiz.result.evaluation_state].bg,
              stateConfig[quiz.result.evaluation_state].border,
            ]"
          >
            <div class="flex items-center gap-3">
              <div
                class="w-10 h-10 rounded-full flex items-center justify-center text-2xl font-bold"
                :class="[
                  stateConfig[quiz.result.evaluation_state].accent,
                  'bg-white/60 dark:bg-black/20',
                ]"
              >
                {{ stateConfig[quiz.result.evaluation_state].icon }}
              </div>
              <div>
                <p
                  class="font-semibold text-lg leading-tight"
                  :class="stateConfig[quiz.result.evaluation_state].text"
                >
                  {{ stateConfig[quiz.result.evaluation_state].label }}
                </p>
                <p
                  class="text-sm opacity-80"
                  :class="stateConfig[quiz.result.evaluation_state].text"
                >
                  {{ quiz.result.feedback }}
                </p>
              </div>
            </div>
          </div>

          <!-- Side-by-side comparison (incorrect/acceptable) or expected only (correct) -->
          <div
            v-if="quiz.result.evaluation_state !== 'correct'"
            class="grid grid-cols-1 sm:grid-cols-2 gap-3"
          >
            <div class="rounded-xl border border-rose-200 dark:border-rose-900/50 bg-rose-50/50 dark:bg-rose-950/20 p-4">
              <p class="text-xs uppercase tracking-wider font-semibold text-rose-700 dark:text-rose-400 mb-2">
                You wrote
              </p>
              <p class="text-base font-medium text-rose-900 dark:text-rose-100 line-through decoration-rose-400/60 break-words">
                {{ submittedAnswer }}
              </p>
            </div>
            <div class="rounded-xl border border-emerald-200 dark:border-emerald-900/50 bg-emerald-50/50 dark:bg-emerald-950/20 p-4">
              <div class="flex items-start justify-between gap-2 mb-2">
                <p class="text-xs uppercase tracking-wider font-semibold text-emerald-700 dark:text-emerald-400">
                  Correct
                </p>
                <button
                  @click="speakSpanish(quiz.result.expected_answer)"
                  class="text-emerald-700 dark:text-emerald-400 hover:scale-110 transition-transform shrink-0"
                  aria-label="Replay audio"
                >
                  🔊
                </button>
              </div>
              <p class="text-base font-medium text-emerald-900 dark:text-emerald-100 break-words">
                {{ quiz.result.expected_answer }}
              </p>
            </div>
          </div>

          <div
            v-else
            class="rounded-xl border border-emerald-200 dark:border-emerald-900/50 bg-emerald-50/50 dark:bg-emerald-950/20 p-4"
          >
            <div class="flex items-start justify-between gap-2 mb-2">
              <p class="text-xs uppercase tracking-wider font-semibold text-emerald-700 dark:text-emerald-400">
                Your answer
              </p>
              <button
                @click="speakSpanish(quiz.result.expected_answer)"
                class="text-emerald-700 dark:text-emerald-400 hover:scale-110 transition-transform shrink-0"
                aria-label="Replay audio"
              >
                🔊
              </button>
            </div>
            <p class="text-base font-medium text-emerald-900 dark:text-emerald-100 break-words">
              {{ quiz.result.expected_answer }}
            </p>
          </div>

          <!-- Alternates -->
          <p v-if="quiz.result.alternate_answers.length" class="text-sm text-muted-foreground px-1">
            <span class="font-medium">Also accepted:</span>
            {{ quiz.result.alternate_answers.join(', ') }}
          </p>

          <!-- Next button -->
          <Button @click="next" class="w-full h-12 text-base font-medium">
            Next question
            <span class="ml-2 text-xs opacity-60 font-normal">↵ Enter</span>
          </Button>
        </div>
      </div>
    </div>
  </div>

  <!-- Mastery modal -->
  <Transition name="fade">
    <div
      v-if="quiz.newlyMastered.length"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      @click.self="dismissMastery"
    >
      <div class="bg-card border border-border rounded-2xl shadow-2xl p-8 max-w-sm w-full mx-4 text-center animate-scale-in">
        <div class="text-5xl mb-4">🏆</div>
        <h2 class="text-2xl font-bold tracking-tight mb-2">Concept mastered!</h2>
        <p class="text-muted-foreground text-sm mb-5">
          You've demonstrated solid understanding of
        </p>
        <div class="flex flex-wrap gap-2 justify-center mb-6">
          <Badge
            v-for="concept in quiz.newlyMastered"
            :key="concept.id"
            class="text-sm px-3 py-1 bg-primary text-primary-foreground"
          >
            {{ concept.name }}
          </Badge>
        </div>
        <Button @click="dismissMastery" class="w-full h-11 font-medium">
          Keep going
        </Button>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
