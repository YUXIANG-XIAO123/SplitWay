import { createApp } from 'vue'

import App from '@/App.vue'
import { setTokenReader, setUnauthorizedHandler } from '@/api/client'
import { readToken, useAuth } from '@/composables/useAuth'
import router from '@/router'

import '@/style.css'

// 让 axios 实例能从身份状态模块读取 token。
// 通过注入而非直接 import，避免 client -> useAuth 的反向依赖。
setTokenReader(readToken)

// 401 处理：清除会话并跳回登录页。
// 该逻辑放在装配层（main.ts），而不是塞进 client.ts，
// 以避免 client -> router -> useAuth -> client 的循环依赖。
const { logout } = useAuth()
setUnauthorizedHandler(() => {
  logout()
  if (router.currentRoute.value.name !== 'login') {
    void router.replace({ name: 'login' })
  }
})

createApp(App).use(router).mount('#app')
