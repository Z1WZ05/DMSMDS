<template>
  <el-card>
    <template #header>
      <div class="card-header">
        <span>📜 超级管理员审计日志</span>
        <el-button type="primary" size="small" @click="fetchData">刷新日志</el-button>
      </div>
    </template>

    <el-table :data="logs" border stripe style="width: 100%" v-loading="loading">
      <el-table-column prop="id" label="记录ID" width="80" />
      <el-table-column prop="create_time" label="操作时间" width="200">
        <template #default="scope">{{ new Date(scope.row.create_time).toLocaleString() }}</template>
      </el-table-column>
      <el-table-column prop="action_type" label="操作类型" width="120">
        <template #default="scope">
          <el-tag :type="scope.row.action_type === 'ALLOCATE' ? 'warning' : 'success'">
            {{ scope.row.action_type }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="details" label="详细描述" />
    </el-table>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const logs = ref([])
const loading = ref(false)

const fetchData = async () => {
  loading.value = true
  try {
    const token = localStorage.getItem('token')
    const res = await axios.get('http://127.0.0.1:8000/business/admin-actions', {
      headers: { Authorization: `Bearer ${token}` }
    })
    logs.value = res.data
  } catch (e) { ElMessage.error('获取日志失败') }
  finally { loading.value = false }
}

onMounted(fetchData)
</script>