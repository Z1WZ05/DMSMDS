<template>
  <el-card>
    <template #header>
      <div class="card-header">
        <span>🧾 处方记录管理</span>
        <el-button type="primary" size="small" @click="fetchData">刷新</el-button>
      </div>
    </template>

    <el-table :data="prescriptions" border stripe style="width: 100%" v-loading="loading">
      <el-table-column prop="prescription_no" label="处方单号" width="220" />
      <el-table-column prop="patient_name" label="病人姓名" width="100" />
      
      <!-- 【修改点】新增开方医生列 -->
      <el-table-column prop="doctor_name" label="开方医生" width="120">
        <template #default="scope">
          <el-tag effect="plain">{{ scope.row.doctor_name || '未知' }}</el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="total_amount" label="总金额" width="100">
        <template #default="scope">
          <span style="color: #67C23A; font-weight: bold;">¥{{ scope.row.total_amount }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="create_time" label="开具时间">
        <template #default="scope">
          {{ new Date(scope.row.create_time).toLocaleString() }}
        </template>
      </el-table-column>
      <el-table-column prop="warehouse_id" label="来源分院" width="120">
        <template #default="scope">
          <el-tag type="info">{{ getBranchName(scope.row.warehouse_id) }}</el-tag>
        </template>
      </el-table-column>
      
      <el-table-column label="操作" width="100">
        <template #default="scope">
          <el-button type="primary" link @click="openDetail(scope.row)">查看详情</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 详情弹窗 -->
    <el-dialog v-model="detailVisible" title="💊 处方药品明细" width="600px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="处方号">{{ currentPres.prescription_no }}</el-descriptions-item>
        <el-descriptions-item label="病人">{{ currentPres.patient_name }}</el-descriptions-item>
        <!-- 【修改点】详情里也显示医生 -->
        <el-descriptions-item label="医生">{{ currentPres.doctor_name }}</el-descriptions-item>
        <el-descriptions-item label="总金额">¥{{ currentPres.total_amount }}</el-descriptions-item>
      </el-descriptions>
      <br>
      <el-table :data="detailItems" border size="small">
        <el-table-column prop="medicine_name" label="药品名称" />
        <el-table-column prop="price_snapshot" label="单价" width="100" />
        <el-table-column prop="quantity" label="数量" width="80" />
        <el-table-column prop="line_total" label="小计" width="100">
          <template #default="scope">¥{{ scope.row.line_total }}</template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const prescriptions = ref([])
const loading = ref(false)
const detailVisible = ref(false)
const currentPres = ref({})
const detailItems = ref([])

const getBranchName = (id) => {
  const map = { 1: '分院1', 2: '分院2', 3: '总院' }
  return map[id] || `未知(${id})`
}

const fetchData = async () => {
  loading.value = true
  try {
    const token = localStorage.getItem('token')
    const res = await axios.get('http://127.0.0.1:8000/business/prescriptions', {
      headers: { Authorization: `Bearer ${token}` }
    })
    prescriptions.value = res.data
  } catch (e) {
    ElMessage.error('加载列表失败')
  } finally {
    loading.value = false
  }
}

const openDetail = async (row) => {
  currentPres.value = row
  detailVisible.value = true
  detailItems.value = [] // 清空旧数据
  try {
    const token = localStorage.getItem('token')
    const res = await axios.get(`http://127.0.0.1:8000/business/prescription/${row.id}/items`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    detailItems.value = res.data
  } catch (e) {
    ElMessage.error('获取明细失败')
  }
}

onMounted(fetchData)
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>