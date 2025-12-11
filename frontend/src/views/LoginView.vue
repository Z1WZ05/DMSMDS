<template>
  <div class="login-container">
    <div class="login-box">
      <div class="title-area">
        <h2>🏥 分布式医疗物资管理系统</h2>
        <p>Distributed Medical Supply Management System</p>
      </div>
      
      <el-form :model="form" class="login-form">
        <el-form-item>
          <el-input v-model="form.username" placeholder="用户名 (如 nurse_1)" :prefix-icon="User" size="large" />
        </el-form-item>
        
        <el-form-item>
          <el-input v-model="form.password" type="password" placeholder="密码" :prefix-icon="Lock" size="large" show-password @keyup.enter="handleLogin"/>
        </el-form-item>

        <el-button type="primary" class="login-btn" :loading="loading" @click="handleLogin" size="large">
          安全登录
        </el-button>
        
        <div class="tips">
          <p>🧪 测试账号:</p>
          <p>分院1 (MySQL): <b>nurse_1</b> / <b>doc_1</b> (密码123)</p>
          <p>总院 (SQL Server): <b>super_admin</b> (密码123)</p>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { User, Lock } from '@element-plus/icons-vue'
import axios from 'axios'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const router = useRouter()
const loading = ref(false)
const form = ref({ username: '', password: '' })

const handleLogin = async () => {
  if(!form.value.username || !form.value.password) return ElMessage.warning('请输入账号密码')

  loading.value = true
  const params = new URLSearchParams()
  params.append('username', form.value.username)
  params.append('password', form.value.password)

  try {
    const res = await axios.post('http://127.0.0.1:8000/auth/login', params)
    const data = res.data

    localStorage.clear()
    
    // 保存用户信息
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('role', data.role)
    localStorage.setItem('username', form.value.username)
    localStorage.setItem('db_name', data.db_name)
    
    ElMessage.success(`登录成功！身份：${data.role}`)
    router.push('/') // 跳转主页
  } catch (e) {
    ElMessage.error('登录失败，请检查账号密码')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container { height: 100vh; display: flex; justify-content: center; align-items: center; background: linear-gradient(135deg, #1c92d2 0%, #f2fcfe 100%); }
.login-box { width: 420px; padding: 40px; background: white; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); text-align: center; }
.title-area h2 { color: #303133; margin-bottom: 5px; }
.title-area p { color: #909399; font-size: 12px; margin-bottom: 30px; }
.login-btn { width: 100%; margin-top: 10px; font-weight: bold; }
.tips { margin-top: 25px; padding: 15px; background: #f4f4f5; border-radius: 4px; text-align: left; font-size: 12px; color: #606266; line-height: 1.8; }
</style>