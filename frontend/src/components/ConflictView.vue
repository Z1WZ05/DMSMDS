<template>
  <div class="conflict-page">
    <el-tabs v-model="activePane" type="border-card">
      
      <!-- 面板 1: 实时报警监控 -->
      <el-tab-pane name="pending">
        <template #label>
          <el-badge :value="pendingList.length" :hidden="pendingList.length === 0" class="badge-item">
            🚨 待处理冲突
          </el-badge>
        </template>

        <div class="pane-header">
          <el-alert title="检测到全院数据不一致，已根据 Owner 策略锁定同步，请人工核实处理。" type="warning" show-icon :closable="false" />
          <el-button type="primary" icon="Refresh" @click="fetchData" style="margin-top: 10px">刷新报警</el-button>
        </div>

        <el-table :data="pendingList" border stripe style="width: 100%; margin-top: 15px">
          <el-table-column prop="create_time" label="检测时间" width="180">
            <template #default="scope">{{ new Date(scope.row.create_time).toLocaleString() }}</template>
          </el-table-column>
          <el-table-column prop="table_name" label="涉及数据表" width="120">
            <template #default="scope"><el-tag>{{ scope.row.table_name }}</el-tag></template>
          </el-table-column>
          <el-table-column prop="conflict_reason" label="🔍 详尽差异报告 (ID | 拥有者值 vs 冲突值)" />
          
          <el-table-column label="决策仲裁" width="380">
            <template #default="scope">
              <el-button-group>
                <el-button type="success" size="small" @click="resolve(scope.row.id, 'mysql')">采纳 MySQL</el-button>
                <el-button type="warning" size="small" @click="resolve(scope.row.id, 'pg')">采纳 PG</el-button>
                <el-button type="danger" size="small" @click="resolve(scope.row.id, 'mssql')">采纳 总院</el-button>
              </el-button-group>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- 面板 2: 冲突处理历史 -->
      <el-tab-pane name="history" label="📜 历史处理记录">
        <el-table :data="historyList" border stripe style="width: 100%">
          <el-table-column prop="resolved_time" label="处理时间" width="180">
            <template #default="scope">{{ new Date(scope.row.resolved_time).toLocaleString() }}</template>
          </el-table-column>
          <el-table-column prop="table_name" label="数据表" width="120" />
          <el-table-column prop="conflict_reason" label="原差异详情" />
          <el-table-column prop="resolution_choice" label="最终决策" width="150">
            <template #default="scope">
              <el-tag type="success" effect="dark">采用 {{ scope.row.resolution_choice }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage, ElLoading } from 'element-plus'

const activePane = ref('pending')
const pendingList = ref([])
const historyList = ref([])

const fetchData = async () => {
  try {
    const token = localStorage.getItem('token')
    const [resPending, resHistory] = await Promise.all([
      axios.get('http://127.0.0.1:8000/conflicts/', { headers: { Authorization: `Bearer ${token}` } }),
      axios.get('http://127.0.0.1:8000/conflicts/history', { headers: { Authorization: `Bearer ${token}` } })
    ])
    pendingList.value = resPending.data
    historyList.value = resHistory.data
  } catch (error) {
    ElMessage.error('获取列表失败')
  }
}

const resolve = async (logId, dbChoice) => {
  const loading = ElLoading.service({ text: '正在跨库强制同步...' })
  try {
    const token = localStorage.getItem('token')
    await axios.post('http://127.0.0.1:8000/conflicts/resolve', {
      log_id: logId,
      db_choice: dbChoice
    }, { headers: { Authorization: `Bearer ${token}` } })
    ElMessage.success(`处理成功：全院已对齐为 ${dbChoice} 的数据`)
    fetchData()
  } catch (error) {
    ElMessage.error('处理失败')
  } finally {
    loading.close()
  }
}

onMounted(fetchData)
</script>

<style scoped>
.conflict-page { padding: 20px; }
.pane-header { margin-bottom: 20px; }
.badge-item { margin-top: 10px; }
</style>