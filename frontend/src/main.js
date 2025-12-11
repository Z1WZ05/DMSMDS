import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue' // 引入图标
import App from './App.vue'
import router from './router' // 引入刚才写的路由配置

const app = createApp(App)

// 注册所有图标 (比如用户头像、锁等)
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(ElementPlus)
app.use(router) // 挂载路由
app.mount('#app')