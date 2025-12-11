<template>
  <el-card class="box-card">
    <template #header>
      <div class="card-header">
        <span>🚨 异常数据冲突监控</span>
        <el-button type="primary" @click="fetchConflicts">刷新列表</el-button>
      </div>
    </template>
    
    <el-empty v-if="conflicts.length === 0" description="暂无冲突，系统运行正常" />

    <el-table v-else :data="conflicts" border style="width: 100%">
      <el-table-column prop="create_time" label="发生时间" width="180" />
      <el-table-column prop="source_db" label="源数据库" width="100" />
      <el-table-column prop="target_db" label="目标数据库" width="100" />
      <el-table-column prop="conflict_reason" label="冲突详情 (Reason)" />
      
      <el-table-column label="人工决策处理" width="300">
        <template #default="scope">
          <el-button type="success" size="small" @click="resolve(scope.row.id, 'source')">
            以分院为准 (覆盖总库)
          </el-button>
          <el-button type="warning" size="small" @click="resolve(scope.row.id, 'target')">
            以总库为准 (覆盖分院)
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const emit = defineEmits(['update-count'])
const conflicts = ref([])

const fetchConflicts = async () => {
  try {
    const res = await axios.get('http://127.0.0.1:8000/conflicts/')
    conflicts.value = res.data
    emit('update-count')
  } catch (error) {
    ElMessage.error('获取冲突日志失败')
  }
}

const resolve = async (logId, choice) => {
  try {
    await axios.post('http://127.0.0.1:8000/conflicts/resolve', {
      log_id: logId,
      choice: choice
    })
    ElMessage.success('处理成功！数据已强制同步。')
    fetchConflicts() // 刷新列表
  } catch (error) {
    ElMessage.error('处理失败')
  }
}

onMounted(fetchConflicts)
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>