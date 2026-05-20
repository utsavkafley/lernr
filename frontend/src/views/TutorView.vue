<script setup lang="ts">
import { ref, watch, nextTick, onMounted, onUnmounted, computed } from 'vue'
import { useStream } from '@/composables/useStream'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

const { messages, isStreaming, currentConcept, lastEvaluation, send, startSession, reset } =
  useStream()

const input = ref('')
const scrollEl = ref<HTMLElement | null>(null)
const inputEl = ref<HTMLInputElement | null>(null)

// Auto-scroll whenever messages change or streaming updates
watch(
  messages,
  () => nextTick(() => scrollEl.value?.scrollTo({ top: scrollEl.value.scrollHeight, behavior: 'smooth' })),
  { deep: true },
)

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey && !isStreaming.value) submit()
}

onMounted(() => {
  startSession()
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
  nextTick(() => inputEl.value?.focus())
}

async function handleReset() {
  reset()
  await startSession()
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
        <!-- Current concept badge -->
        <div
          v-if="currentConcept"
          class="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-primary/10 border border-primary/20 animate-fade-up"
        >
          <span class="w-1.5 h-1.5 rounded-full bg-primary animate-pulse"></span>
          <span class="text-xs font-semibold text-primary truncate max-w-[160px]">{{ currentConcept }}</span>
        </div>
        <!-- Last evaluation pill -->
        <span
          v-if="evalLabel && !isStreaming"
          class="text-xs font-semibold tabular-nums animate-fade-up"
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
        <div class="text-center space-y-3">
          <div class="w-12 h-12 rounded-full bg-primary/10 mx-auto flex items-center justify-center text-2xl">
            🧠
          </div>
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
            <span>{{ msg.content }}</span>
            <span
              v-if="isStreaming && idx === messages.length - 1 && msg.role === 'assistant'"
              class="inline-block w-0.5 h-3.5 bg-current ml-0.5 align-middle animate-pulse"
            />
          </div>
        </div>
      </template>

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
      The tutor focuses on your weakest concepts first.
    </p>
  </div>
</template>
