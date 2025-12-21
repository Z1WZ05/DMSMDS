<!-- frontend/src/components/RiskCenter.vue 完整代码 -->
<template>
  <el-card shadow="never" class="risk-card">
    <template #header>
      <div class="header">
        <span class="title">🚀 全院风险审计中心 (超级管理员)</span>
        <el-button type="primary" size="small" @click="fetchAlerts">同步最新预警</el-button>
      </div>
    </template>

    <el-table :data="alerts" border stripe style="width: 100%">
      <el-table-column prop="create_time" label="预警时间" width="200">
        <template #default="scope">{{ new Date(scope.row.create_time).toLocaleString() }}</template>
      </el-table-column>
      <el-table-column prop="warehouse_id" label="发生院区" width="120">
        <template #default="scope">
          <el-tag>{{ getBranchName(scope.row.warehouse_id) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="message" label="报警详情描述" />
      <el-table-column label="风险评估" width="120">
        <template #default="scope">
          <el-tag type="danger" effect="dark">高风险操作</el-tag>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const alerts = ref([])
const getBranchName = (id) => ({1:'分院1', 2:'分院2', 3:'总院'}[id] || id)

const fetchAlerts = async () => {
  const token = localStorage.getItem('token')
  try {
    const res = await axios.get('http://127.0.0.1:8000/advanced/alerts', {
      headers: { Authorization: `Bearer ${token}` }
    })
    alerts.value = res.data
  } catch (e) { ElMessage.error('加载预警失败') }
}
onMounted(fetchAlerts)
</script>