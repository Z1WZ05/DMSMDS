<template>
  <el-card>
    <template #header>
      <div class="card-header">
        <span>📝 我的操作记录流水</span>
      </div>
    </template>

    <el-table :data="records" stripe style="width: 100%" v-loading="loading">
      <el-table-column prop="create_time" label="操作时间" width="200">
        <template #default="scope">
          {{ new Date(scope.row.create_time).toLocaleString() }}
        </template>
      </el-table-column>
      
      <el-table-column prop="operation_type" label="类型" width="120">
        <template #default="scope">
          <el-tag :type="scope.row.operation_type.includes('ALLOCATE') ? 'warning' : ''">
            {{ scope.row.operation_type }}
          </el-tag>
        </template>
      </el-table-column>
      
      <!-- 新增：业务详情 -->
      <el-table-column prop="description" label="业务详情" width="250">
        <template #default="scope">
          <span style="font-family: monospace; font-size: 12px;">{{ scope.row.description || '-' }}</span>
        </template>
      </el-table-column>

      <el-table-column prop="medicine_name" label="药品名称" />
      
      <el-table-column prop="change_amount" label="库存变动">
        <template #default="scope">
          <span :style="{ color: scope.row.change_amount < 0 ? 'red' : 'green', fontWeight: 'bold' }">
            {{ scope.row.change_amount > 0 ? '+' : '' }}{{ scope.row.change_amount }}
          </span>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const records = ref([])
const loading = ref(false)

const fetchRecords = async () => {
  loading.value = true
  try {
    const token = localStorage.getItem('token')
    const res = await axios.get('http://127.0.0.1:8000/business/my-records', {
      headers: { Authorization: `Bearer ${token}` }
    })
    records.value = res.data
  } catch (e) {
    ElMessage.error('获取记录失败')
  } finally {
    loading.value = false
  }
}

onMounted(fetchRecords)
</script>
<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>