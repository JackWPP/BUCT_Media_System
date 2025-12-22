/**
 * 应用入口
 */
import { createApp } from 'vue'
import naive from 'naive-ui'
import App from './App.vue'
import router from './router'
import pinia from './stores'
import { vPermission } from './directives/permission'

const app = createApp(App)

// 注册全局指令
app.directive('permission', vPermission)

app.use(naive)
app.use(pinia)
app.use(router)

app.mount('#app')

