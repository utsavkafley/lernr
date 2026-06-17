import { createRouter, createWebHistory} from 'vue-router'
import {useAuthStore} from '@/stores/auth'

const router = createRouter({
    history: createWebHistory(),
    routes: [
        {path:'/login', component:()=> import('@/views/LoginView.vue'), meta: {public: true} },
        {path:'/', component:()=>import('@/views/HomeView.vue')},
        {path:'/tracks', component:()=>import('@/views/TracksView.vue')},
        {path:'/practice', component:()=>import('@/views/PracticeView.vue')},
        {path:'/verbs', component:()=>import('@/views/VerbsView.vue')},
        {path:'/progress', component:()=>import('@/views/ProgressView.vue')},
        {path:'/tutor', component:()=>import('@/views/TutorView.vue')},
        {path:'/:pathMatch(.*)*', redirect: '/'},
    ],
})

router.beforeEach((to)=>{
    const auth = useAuthStore()
    if(!to.meta.public && !auth.token){
        return '/login'
    }
    if(to.path=='/login' && auth.token){
        return '/'
    }
})

export default router