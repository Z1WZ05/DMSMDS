<template>
  <el-card>
    <template #header>
      <div class="card-header">
        <div class="title-box">
          <span>📦 药品库存总览</span>
          <el-tag v-if="!canSwitchDb" type="info" class="ml-2">
            当前院区: {{ currentDbName }}
          </el-tag>
        </div>
        
        <!-- 只有超级管理员(super_admin)才能切换查看其他院区 -->
        <el-select 
          v-if="canSwitchDb" 
          v-model="selectedDb" 
          placeholder="切换院区视图" 
          @change="fetchData" 
          style="width: 200px;">
          <el-option label="第一分院 (MySQL)" value="mysql" />
          <el-option label="第二分院 (PG)" value="pg" />
          <el-option label="总院 (MSSQL)" value="mssql" />
        </el-select>
      </div>
    </template>

    <el-table :data="mergedData" stripe style="width: 100%" v-loading="loading">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="name" label="药品名称" width="180" />
      <el-table-column prop="category" label="分类" width="100" />
      <el-table-column prop="price" label="单价(元)" width="100" />
      
      <!-- 新增：显示库存 -->
      <el-table-column prop="quantity" label="当前库存" width="120">
        <template #default="scope">
          <span :class="{'low-stock': scope.row.quantity < 20}">
            {{ scope.row.quantity }} 
            <el-tag size="small" type="danger" v-if="scope.row.quantity < 20">紧缺</el-tag>
          </span>
        </template>
      </el-table-column>

      <el-table-column prop="danger_level" label="管控等级" width="120">
        <template #default="scope">
          <el-tag :type="getRiskTagType(scope.row.danger_level)">
            {{ scope.row.danger_level }}
          </el-tag>
        </template>
      </el-table-column>
      
      <el-table-column label="操作" min-width="150">
        <template #default="scope">
           <!-- 超管功能：制造冲突 -->
           <el-button 
             v-if="userRole === 'super_admin' && selectedDb === 'mssql'" 
             type="danger" plain size="small" 
             @click="simulateConflict(scope.row)">
             修改库存(测)
           </el-button>

           <!-- 医护功能：开药 (管理员不能开) -->
           <el-button 
             v-if="!userRole.includes('admin')" 
             type="primary" size="small" 
             @click="openPrescribeDialog(scope.row)">
             开药
           </el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'

const userRole = localStorage.getItem('role') || ''
const userDb = localStorage.getItem('db_name') || 'mysql'

// 权限判断：只有 super_admin 可以切换视角
const canSwitchDb = computed(() => userRole === 'super_admin')

// 如果不能切换，就锁定在用户自己的 db
const selectedDb = ref(canSwitchDb.value ? 'mssql' : userDb)

const medicines = ref([])
const inventoryMap = ref({}) // 存储 {medicine_id: quantity}
const loading = ref(false)

const dbNames = {
  'mysql': '第一分院 (MySQL)',
  'pg': '第二分院 (PostgreSQL)',
  'mssql': '集团总院 (SQL Server)'
}
const currentDbName = computed(() => dbNames[selectedDb.value])

// 合并药品信息和库存信息
const mergedData = computed(() => {
  return medicines.value.map(med => ({
    ...med,
    quantity: inventoryMap.value[med.id] || 0 // 匹配库存
  }))
})

const getRiskTagType = (level) => {
  if (level.includes('急救')) return 'danger'
  if (level === '处方药') return 'warning'
  return 'success'
}

const fetchData = async () => {
  loading.value = true
  try {
    // 1. 获取药品列表 (基础信息)
    const resMed = await axios.get(`http://127.0.0.1:8000/medicines/${selectedDb.value}`)
    medicines.value = resMed.data
    
    // 2. 获取库存信息 (需要后端新增一个接口，或者复用 analysis)
    // 为了简单，我们临时写一个逻辑：
    // 这里其实应该有一个 /inventory/{db_name} 接口，但我们之前的 analysis/inventory-value 是聚合的。
    // 【临时方案】：我们假设 medicines 接口返回的数据里还没库存。
    // 我们需要去后端加一个接口，或者在 /medicines 接口里把库存带上。
    
    // 这里的逻辑有点卡壳，因为之前的 /medicines 接口只查了 medicine 表。
    // 我们去后端 business.py 加一个 "查询带库存的药品列表" 接口吧。
    // 假设现在有了：GET /business/stock/{db_name}
    const resInv = await axios.get(`http://127.0.0.1:8000/business/stock/${selectedDb.value}`)
    
    // 转换库存数据格式
    const map = {}
    resInv.data.forEach(item => {
      map[item.medicine_id] = item.quantity
    })
    inventoryMap.value = map

  } catch (error) {
    ElMessage.error('数据加载失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

// ... (simulateConflict 和 openPrescribeDialog 代码保持不变，复制过来即可) ...
const openPrescribeDialog = (row) => {
  ElMessageBox.prompt(`开具 ${row.name} 数量：`, '医生开药', {
    confirmButtonText: '确认开方',
    inputPattern: /^\d+$/,
    inputErrorMessage: '请输入数字'
  }).then(async ({ value }) => {
    try {
      const token = localStorage.getItem('token')
      await axios.post('http://127.0.0.1:8000/business/prescribe', {
        medicine_id: row.id,
        quantity: parseInt(value)
      }, {
        headers: { Authorization: `Bearer ${token}` }
      })
      ElMessage.success('开药成功！库存已自动扣减。')
      fetchData() // 刷新列表
    } catch (e) {
      ElMessage.error(e.response?.data?.detail || '开药失败')
    }
  })
}

// 模拟冲突代码复制过来...
const simulateConflict = (row) => {
    // ... 代码同前 ...
    ElMessageBox.prompt('输入新库存（总院强制修改）', '制造冲突', {
      confirmButtonText: '确定',
      inputPattern: /^\d+$/
    }).then(async ({ value }) => {
       await axios.post('http://127.0.0.1:8000/medicines/simulate-central-update', null, {
        params: { warehouse_id: 1, medicine_id: row.id, new_quantity: value }
      })
      ElMessage.success('冲突已制造，请观察监控')
    })
}

onMounted(fetchData)
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
.title-box { display: flex; align-items: center; }
.ml-2 { margin-left: 10px; }
.low-stock { color: red; font-weight: bold; }
</style>