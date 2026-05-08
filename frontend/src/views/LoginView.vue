<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

const router = useRouter()
const auth = useAuthStore()

const mode = ref<'login' | 'register'>('login')
const email = ref('')
const password = ref('')
const username = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  loading.value = true
  try {
    if (mode.value === 'login') {
      await auth.login(email.value, password.value)
    } else {
      await auth.register(email.value, password.value, username.value)
    }
    router.push('/tracks')
  } catch (err: any) {
    error.value = err.response?.data?.detail ?? 'Something went wrong'
  } finally {
    loading.value = false
  }
}

function toggleMode() {
  mode.value = mode.value === 'login' ? 'register' : 'login'
  error.value = ''
}
</script>

<template>
  <div class="min-h-[calc(100vh-5rem)] flex items-center justify-center -mt-10">
    <div class="w-full max-w-md animate-fade-up">
      <!-- Brand -->
      <div class="text-center mb-10">
        <div class="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-primary to-accent-foreground text-primary-foreground font-bold text-2xl shadow-lg shadow-primary/20 mb-5">
          L
        </div>
        <h1 class="text-4xl font-bold tracking-tight mb-2">
          {{ mode === 'login' ? 'Welcome back' : 'Start practicing' }}
        </h1>
        <p class="text-muted-foreground">
          {{ mode === 'login' ? 'Pick up where you left off' : 'Build your Spanish through patterns, not memorization' }}
        </p>
      </div>

      <!-- Form -->
      <div class="bg-card border border-border/60 rounded-2xl p-8 shadow-xl shadow-foreground/5">
        <form @submit.prevent="submit" class="space-y-4">
          <div v-if="mode === 'register'" class="space-y-1.5">
            <label class="text-sm font-medium">Username</label>
            <Input v-model="username" placeholder="your_name" required class="h-11" />
          </div>
          <div class="space-y-1.5">
            <label class="text-sm font-medium">Email</label>
            <Input v-model="email" type="email" placeholder="you@example.com" required class="h-11" />
          </div>
          <div class="space-y-1.5">
            <label class="text-sm font-medium">Password</label>
            <Input v-model="password" type="password" placeholder="••••••••" required class="h-11" />
          </div>

          <p v-if="error" class="text-sm text-destructive bg-destructive/10 px-3 py-2 rounded-lg">
            {{ error }}
          </p>

          <Button type="submit" class="w-full h-11 text-base font-medium" :disabled="loading">
            {{ loading ? 'Loading…' : mode === 'login' ? 'Sign in' : 'Create account' }}
          </Button>
        </form>

        <p class="text-center text-sm text-muted-foreground mt-6">
          {{ mode === 'login' ? "New here?" : 'Already have an account?' }}
          <button @click="toggleMode" class="text-foreground font-medium underline-offset-4 hover:underline ml-1">
            {{ mode === 'login' ? 'Create an account' : 'Sign in' }}
          </button>
        </p>
      </div>
    </div>
  </div>
</template>
