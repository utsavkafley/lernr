import { createRouter, createWebHistory} from 'vue-router'
import {useAuthStore} from '@/stores/auth'

const router = createRouter({
    history: createWebHistory(),
    routes: [
        {path:'/login', component:()=> import('@/views/LoginView.vue'), meta: {public: true} },
        {path:'/tracks', component:()=>import('@/views/TracksView.vue')},
        {path:'/practice', component:()=>import('@/views/PracticeView.vue')},
        {path:'/progress', component:()=>import('@/views/ProgressView.vue')},
        {path:'/:pathMatch(.*)*', redirect: '/tracks'},
    ],
})

router.beforeEach((to)=>{
    const auth = useAuthStore()
    if(!to.meta.public && !auth.token){
        return '/login'
    }
    if(to.path=='/login' && auth.token){
        return '/tracks'
    }
})

export default router