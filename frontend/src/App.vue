<script setup lang="ts">
import { RouterView, RouterLink, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { usePlayerStore } from '@/stores/player'
import { Button } from '@/components/ui/button'
import AudioPlayer from '@/components/AudioPlayer.vue'
import logoUrl from '@/assets/lernr_logo_web.png'

const auth = useAuthStore()
const route = useRoute()
const player = usePlayerStore()

function logout() {
  auth.logout()
  window.location.href = '/login'
}

const navItems = [
  { to: '/tracks', label: 'Tracks' },
  { to: '/practice', label: 'Practice' },
  { to: '/tutor', label: 'Tutor' },
  { to: '/progress', label: 'Progress' },
]
</script>

<template>
  <div class="min-h-screen text-foreground">
    <!-- Nav -->
    <header
      v-if="auth.isAuthenticated"
      class="border-b border-border/60 sticky top-0 z-10 backdrop-blur-md bg-background/70"
    >
      <div class="max-w-5xl mx-auto px-6 h-16 flex items-center justify-between">
        <div class="flex items-center gap-1">
          <RouterLink to="/" class="flex items-center gap-2.5 mr-6 group">
            <img
              :src="logoUrl"
              alt="lernr"
              class="w-14 h-14 rounded-lg object-cover shadow-sm ring-1 ring-border/50 group-hover:scale-105 transition-transform"
            />
          </RouterLink>
          <nav class="flex items-center gap-1">
            <RouterLink
              v-for="item in navItems"
              :key="item.to"
              :to="item.to"
              class="text-sm px-4 py-1.5 rounded-full transition-all font-medium"
              :class="route.path === item.to
                ? 'bg-foreground text-background'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted'"
            >
              {{ item.label }}
            </RouterLink>
          </nav>
        </div>
        <div class="flex items-center gap-3">
          <span v-if="auth.user" class="text-sm text-muted-foreground hidden sm:block">
            {{ auth.user.username }}
          </span>
          <Button variant="ghost" size="sm" @click="logout">Log out</Button>
        </div>
      </div>
    </header>

    <!-- Page content -->
    <main
      class="max-w-5xl mx-auto px-6 py-10"
      :class="player.activeTrackNumber !== null ? 'pb-52' : ''"
    >
      <RouterView v-slot="{ Component, route: r }">
        <Transition name="page" mode="out-in">
          <component :is="Component" :key="r.path" />
        </Transition>
      </RouterView>
    </main>

    <AudioPlayer />
  </div>
</template>

<style scoped>
.page-enter-active,
.page-leave-active {
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}
.page-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.page-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
