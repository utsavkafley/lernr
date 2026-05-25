<script setup lang="ts">
import { ref, watch, nextTick, onMounted, onUnmounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useStream } from '@/composables/useStream'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import tutorIllustration from '@/assets/tutor_question.svg'
import happyIllustration from '@/assets/feeling_happy.svg'

function renderMarkdown(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
}

const route = useRoute()
const router = useRouter()

const {
  messages, isStreaming,
  currentConcept, currentConceptId, lastEvaluation,
  currentStep, totalSteps, suggestQuiz, chatScore,
  send, startSession, reset,
} = useStream()

const conceptIdFromRoute = computed(() => {
  const v = route.query.concept_id
  return v ? Number(v) : null
})
const conceptNameFromRoute = computed(() => {
  return route.query.concept_name as string | undefined
})

const input = ref('')
const scrollEl = ref<HTMLElement | null>(null)
const inputEl = ref<InstanceType<typeof import('@/components/ui/input').Input> | null>(null)

// Auto-scroll whenever messages change or streaming updates
watch(
  messages,
  () => nextTick(() => scrollEl.value?.scrollTo({ top: scrollEl.value.scrollHeight, behavior: 'smooth' })),
  { deep: true },
)

// Refocus input whenever streaming finishes
watch(isStreaming, (streaming) => {
  if (!streaming) nextTick(() => inputEl.value?.$el?.focus())
})

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey && !isStreaming.value) submit()
}

onMounted(() => {
  startSession(conceptIdFromRoute.value)
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})

async function submit() {
  const msg = input.value.trim()
  if (!msg || isStreaming.value) return
  input.value = ''
  await send(msg)
  nextTick(() => inputEl.value?.$el?.focus())
}

async function handleReset() {
  reset()
  await startSession(conceptIdFromRoute.value)
}

const evalColor = computed(() => {
  if (lastEvaluation.value === 'correct') return 'text-emerald-500'
  if (lastEvaluation.value === 'acceptable') return 'text-amber-500'
  if (lastEvaluation.value === 'incorrect') return 'text-rose-500'
  return ''
})

const evalLabel = computed(() => {
  if (lastEvaluation.value === 'correct') return '✓ Correct'
  if (lastEvaluation.value === 'acceptable') return '~ Close'
  if (lastEvaluation.value === 'incorrect') return '× Not quite'
  return ''
})
</script>

<template>
  <div class="max-w-2xl mx-auto flex flex-col" style="height: calc(100vh - 10rem)">
    <!-- Header -->
    <div class="flex items-end justify-between mb-5 animate-fade-up shrink-0">
      <div>
        <p class="text-sm font-medium text-primary uppercase tracking-wider mb-1">AI Tutor</p>
        <h1 class="text-3xl font-bold tracking-tight">Socratic session</h1>
      </div>
      <div class="flex items-center gap-3">
        <!-- Concept + step progress -->
        <div
          v-if="currentConcept"
          class="flex flex-col items-end gap-1 animate-fade-up"
        >
          <div class="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-primary/10 border border-primary/20">
            <span class="w-1.5 h-1.5 rounded-full bg-primary animate-pulse shrink-0"></span>
            <span class="text-xs font-semibold text-primary truncate max-w-[160px]">{{ currentConcept }}</span>
          </div>
          <!-- Step progress dots -->
          <div v-if="totalSteps > 0" class="flex items-center gap-1 px-1">
            <span
              v-for="i in totalSteps"
              :key="i"
              class="w-1.5 h-1.5 rounded-full transition-all duration-300"
              :class="i <= currentStep ? 'bg-primary' : 'bg-muted-foreground/30'"
            />
          </div>
        </div>

        <!-- Last evaluation pill -->
        <span
          v-if="evalLabel && !isStreaming"
          class="text-xs font-semibold animate-fade-up"
          :class="evalColor"
        >
          {{ evalLabel }}
        </span>
        <Button variant="ghost" size="sm" @click="handleReset" :disabled="isStreaming" class="text-muted-foreground">
          Restart
        </Button>
      </div>
    </div>

    <!-- Message thread -->
    <div
      ref="scrollEl"
      class="flex-1 overflow-y-auto rounded-2xl border border-border/60 bg-card p-4 space-y-4 scroll-smooth"
    >
      <!-- Empty / loading state -->
      <div v-if="messages.length === 0" class="h-full flex items-center justify-center">
        <div class="text-center space-y-4">
          <img :src="tutorIllustration" alt="" aria-hidden="true" class="w-48 mx-auto animate-float" />
          <p class="text-sm text-muted-foreground">Starting your session…</p>
        </div>
      </div>

      <template v-else>
        <div
          v-for="(msg, idx) in messages"
          :key="idx"
          class="flex animate-fade-up"
          :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
        >
          <!-- Assistant avatar -->
          <div
            v-if="msg.role === 'assistant'"
            class="w-7 h-7 rounded-full bg-gradient-to-br from-primary to-accent-foreground flex items-center justify-center text-primary-foreground text-xs font-bold mr-2 mt-0.5 shrink-0"
          >
            L
          </div>

          <div
            class="max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed"
            :class="
              msg.role === 'assistant'
                ? 'bg-muted text-foreground rounded-tl-sm'
                : 'bg-primary text-primary-foreground rounded-tr-sm'
            "
          >
            <!-- Streaming cursor on last assistant message -->
            <span v-html="renderMarkdown(msg.content)" />
            <span
              v-if="isStreaming && idx === messages.length - 1 && msg.role === 'assistant'"
              class="inline-block w-0.5 h-3.5 bg-current ml-0.5 align-middle animate-pulse"
            />
          </div>
        </div>
      </template>

      <!-- Quiz nudge — rendered as an interactive card, not prose -->
      <div
        v-if="suggestQuiz && !isStreaming"
        class="flex justify-start animate-fade-up"
      >
        <div class="max-w-[80%] rounded-2xl rounded-tl-sm bg-primary/10 border border-primary/20 px-4 py-3 flex items-center gap-4">
          <img :src="happyIllustration" alt="" aria-hidden="true" class="w-16 shrink-0 hidden sm:block" />
          <div class="space-y-2">
            <p class="text-sm font-medium text-primary">
              You're getting this! Lock it in with the quiz.
            </p>
            <p class="text-xs text-muted-foreground">
              Chat score: {{ Math.round(chatScore * 100) }}% — take the quiz to push it to mastery.
            </p>
            <button
              @click="router.push({ path: '/practice', query: { concept_id: currentConceptId, concept_name: currentConcept } })"
              class="text-xs font-semibold px-3 py-1.5 rounded-lg bg-primary text-primary-foreground hover:opacity-90 transition-opacity"
            >
              Take the quiz on "{{ currentConcept }}" →
            </button>
          </div>
        </div>
      </div>

      <!-- Typing indicator while waiting for first token -->
      <div
        v-if="isStreaming && (messages.length === 0 || messages[messages.length - 1].role === 'user')"
        class="flex justify-start animate-fade-up"
      >
        <div class="w-7 h-7 rounded-full bg-gradient-to-br from-primary to-accent-foreground flex items-center justify-center text-primary-foreground text-xs font-bold mr-2 mt-0.5 shrink-0">
          L
        </div>
        <div class="bg-muted rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-1">
          <span class="w-1.5 h-1.5 rounded-full bg-muted-foreground/60 animate-bounce" style="animation-delay: 0ms" />
          <span class="w-1.5 h-1.5 rounded-full bg-muted-foreground/60 animate-bounce" style="animation-delay: 150ms" />
          <span class="w-1.5 h-1.5 rounded-full bg-muted-foreground/60 animate-bounce" style="animation-delay: 300ms" />
        </div>
      </div>
    </div>

    <!-- Input bar -->
    <div class="mt-3 flex gap-2 shrink-0 animate-fade-up">
      <Input
        ref="inputEl"
        v-model="input"
        placeholder="Type your Spanish answer…"
        :disabled="isStreaming"
        class="h-12 text-base"
        autofocus
      />
      <Button
        @click="submit"
        :disabled="!input.trim() || isStreaming"
        class="h-12 px-6 font-medium shrink-0"
      >
        Send
        <span class="ml-2 text-xs opacity-60 font-normal">↵</span>
      </Button>
    </div>
    <p class="text-center text-xs text-muted-foreground mt-2">
      {{ conceptNameFromRoute ? `Focused on: ${conceptNameFromRoute}` : 'Reinforcing concepts closest to mastery' }}
    </p>
  </div>
</template>
