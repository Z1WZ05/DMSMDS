<template>
  <el-card header="⚙️ 系统数据同步与维护中心" style="max-width: 800px; margin: 20px auto;">
    <el-form :model="form" label-width="160px">
      <el-divider content-position="left">同步与邮件策略</el-divider>
      <el-form-item label="实时同步">
        <el-switch v-model="form.real_time" />
      </el-form-item>
      <el-form-item label="定时轮询同步">
        <el-switch v-model="form.scheduled" />
      </el-form-item>
      <el-form-item label="轮询周期 (秒)">
        <el-input-number v-model="form.interval" :min="1" :max="3600" />
      </el-form-item>
      <el-form-item label="管理员邮箱">
        <el-input v-model="form.admin_email" />
      </el-form-item>
      <el-form-item label="SMTP 授权码">
        <el-input v-model="form.smtp_password" type="password" show-password />
      </el-form-item>
      <el-form-item label="系统访问 URL">
        <el-input v-model="form.frontend_url" placeholder="用于邮件跳转" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="saveSettings">保存策略配置</el-button>
      </el-form-item>

      <el-divider content-position="left">高级维护工具 (3.f & 4.1)</el-divider>
      <el-row :gutter="20">
        <el-col :span="12">
          <el-card shadow="hover" class="tool-card">
            <template #header><b>数据导出 (3.f)</b></template>
            <p class="desc">下载总库 (MSSQL) 的全量 SQL 备份，包含表结构、用户及所有业务记录。</p>
            <el-button type="info" @click="handleBackup" icon="Download">生成备份文件</el-button>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card shadow="hover" class="tool-card">
            <template #header><b>整库迁移 (4.1)</b></template>
            <p class="desc">强制清空分院2并从分院1克隆全量数据。用于解决异构数据库数据失步。</p>
            <el-button type="danger" @click="handleMigrate" icon="Connection">执行 MySQL -> PG 迁移</el-button>
          </el-card>
        </el-col>
      </el-row>
    </el-form>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox, ElLoading } from 'element-plus'

const form = ref({
  real_time: true, scheduled: true, interval: 10,
  admin_email: '', smtp_password: '', frontend_url: ''
})

const fetchSettings = async () => {
  const token = localStorage.getItem('token')
  try {
    const res = await axios.get('http://127.0.0.1:8000/settings/', {
      headers: { Authorization: `Bearer ${token}` }
    })
    form.value = res.data
  } catch (e) { ElMessage.error('加载设置失败') }
}

const saveSettings = async () => {
  const token = localStorage.getItem('token')
  try {
    await axios.put('http://127.0.0.1:8000/settings/', form.value, {
      headers: { Authorization: `Bearer ${token}` }
    })
    ElMessage.success('配置已保存')
  } catch (e) { ElMessage.error('保存失败') }
}

// 【修复逻辑】处理备份下载
const handleBackup = () => {
  const token = localStorage.getItem('token')
  if (!token) return
  // 将 Token 作为参数放入 URL，解决 window.open 无法传 Header 的问题
  const downloadUrl = `http://127.0.0.1:8000/maintenance/backup/mssql?token=${token}`
  window.location.href = downloadUrl // 触发浏览器下载
}

// 【修复逻辑】处理迁移
const handleMigrate = () => {
  ElMessageBox.confirm(
    '此操作将永久抹除分院2(PostgreSQL)的所有旧数据并从分院1(MySQL)完整覆盖，是否继续？',
    '高风险操作警告',
    { confirmButtonText: '确定执行', cancelButtonText: '取消', type: 'error' }
  ).then(async () => {
    const loading = ElLoading.service({ text: '正在跨库传输大数据量中，请稍后...' })
    try {
      const token = localStorage.getItem('token')
      const res = await axios.post('http://127.0.0.1:8000/maintenance/migrate', null, {
        params: { source_db: 'mysql', target_db: 'pg' },
        headers: { Authorization: `Bearer ${token}` }
      })
      ElMessage.success(res.data.message)
    } catch (e) {
      ElMessage.error('迁移失败：' + (e.response?.data?.detail || '网络异常'))
    } finally {
      loading.close()
    }
  })
}

onMounted(fetchSettings)
</script>

<style scoped>
.tool-card { background-color: #f9f9f9; text-align: center; }
.desc { font-size: 12px; color: #909399; margin: 10px 0 20px; line-height: 1.5; height: 36px; }
</style>