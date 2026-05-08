import {defineStore} from 'pinia'
import {ref, computed} from 'vue'
import api from '@/composables/useApi'

interface User {
    id: string
    email: string
    username: string
}

export const useAuthStore = defineStore('auth', ()=>{
    const token = ref<string | null>(localStorage.getItem('token'))
    const user = ref<User | null>(null)

    const isAuthenticated = computed(()=>!!token.value)

    function setToken(t: string) {
        token.value = t
        localStorage.setItem('token', t)
    }

    function clear() {
        token.value = null
        user.value = null
        localStorage.removeItem('token')
    }

    async function login(email: string, password:string){
        const {data} = await api.post('/auth/login', {email, password})
        setToken(data.access_token)
    }

    async function register(email:string, password:string, username:string){
        const {data} = await api.post('auth/register', {email, password, username})
        setToken(data.access_token)
    }

    async function fetchMe() {
        const {data} = await api.get('/auth/me')
        user.value = data
    }

    function logout(){
        clear()
    }

    return {token, user, isAuthenticated, login, register, fetchMe, logout}
})
