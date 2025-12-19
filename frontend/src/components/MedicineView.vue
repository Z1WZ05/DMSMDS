<template>
  <div class="medicine-view">
    <el-row :gutter="20">
      <!-- 左侧：药品列表 -->
      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <div class="title-box">
                <span>📦 药品库存总览</span>
                <el-tag v-if="!canSwitchDb" type="info" class="ml-2">
                  当前院区: {{ currentDbName }}
                </el-tag>
              </div>
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
            <el-table-column prop="name" label="药品名称" width="150" />
            <el-table-column prop="category" label="分类" width="100" />
            <el-table-column prop="price" label="单价" width="80" />
            <el-table-column prop="quantity" label="库存" width="100">
              <template #default="scope">
                <span :class="{'low-stock': scope.row.quantity < 20}">{{ scope.row.quantity }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="danger_level" label="等级" width="100">
              <template #default="scope">
                <el-tag :type="getRiskTagType(scope.row.danger_level)" size="small">
                  {{ scope.row.danger_level }}
                </el-tag>
              </template>
            </el-table-column>
            
            <el-table-column label="操作" min-width="120">
              <template #default="scope">
                 <!-- 医护功能：加入清单 -->
                 <el-button 
                   v-if="!userRole.includes('admin')" 
                   type="success" plain size="small" 
                   @click="addToCart(scope.row)">
                   + 加入清单
                 </el-button>
                 
                 <!-- 超管功能：调拨 -->
                 <el-button 
                   v-if="userRole === 'super_admin' && selectedDb === 'mssql'" 
                   type="warning" size="small" 
                   @click="openAllocationDialog(scope.row)">
                   调拨
                 </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- 右侧：处方篮 (仅医护可见) -->
      <el-col :span="8" v-if="!userRole.includes('admin')">
        <el-card class="cart-card">
          <template #header>
            <div class="card-header">
              <span>📝 待开处方清单</span>
              <el-tag type="warning" effect="dark">{{ cart.length }} 项</el-tag>
            </div>
          </template>

          <div v-if="cart.length === 0" class="empty-cart">
            <el-empty description="暂无药品，请从左侧添加" :image-size="80" />
          </div>

          <div v-else>
            <div v-for="(item, index) in cart" :key="item.id" class="cart-item">
              <div class="item-info">
                <div class="item-name">{{ item.name }}</div>
                <div class="item-price">¥{{ item.price }} × </div>
              </div>
              <div class="item-action">
                <el-input-number v-model="item.count" :min="1" :max="item.maxStock" size="small" style="width: 100px" />
                <el-button type="danger" link size="small" @click="removeFromCart(index)">删除</el-button>
              </div>
            </div>

            <div class="cart-footer">
              <div class="total-price">
                预估总价: <span>¥{{ cartTotal.toFixed(2) }}</span>
              </div>
              <el-button type="primary" class="submit-btn" @click="openPrescribeDialog" size="large">
                生成处方并结算
              </el-button>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 结算弹窗 -->
    <el-dialog v-model="prescribeDialog.visible" title="✅ 确认处方信息" width="400px">
      <el-form label-width="80px">
        <el-form-item label="病人姓名">
          <el-input v-model="prescribeDialog.patientName" placeholder="请输入病人真实姓名" />
        </el-form-item>
        <el-divider>药品明细</el-divider>
        <div v-for="item in cart" :key="item.id" class="dialog-item">
          <span>{{ item.name }}</span>
          <span>x {{ item.count }}</span>
        </div>
        <el-divider />
        <div class="dialog-total">总金额：¥{{ cartTotal.toFixed(2) }}</div>
      </el-form>
      <template #footer>
        <el-button @click="prescribeDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitPrescription" :loading="submitting">确认提交</el-button>
      </template>
    </el-dialog>

    <!-- 调拨弹窗 (已升级：支持任意库之间调拨) -->
    <el-dialog v-model="allocDialog.visible" title="🚚 全网物资调拨指令" width="450px">
      <el-form label-width="80px">
        <el-form-item label="调拨药品">
          <el-input v-model="allocDialog.medicineName" disabled />
        </el-form-item>
        
        <el-form-item label="调出仓库">
          <el-select v-model="allocDialog.sourceBranchId" placeholder="选择发货方">
            <el-option label="第一分院 (MySQL)" :value="1" />
            <el-option label="第二分院 (PostgreSQL)" :value="2" />
            <el-option label="集团总库 (MSSQL)" :value="3" />
          </el-select>
        </el-form-item>

        <el-form-item label="调入仓库">
          <el-select v-model="allocDialog.targetBranchId" placeholder="选择接收方">
            <el-option label="第一分院 (MySQL)" :value="1" />
            <el-option label="第二分院 (PostgreSQL)" :value="2" />
            <el-option label="集团总库 (MSSQL)" :value="3" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="调拨数量">
          <el-input-number v-model="allocDialog.quantity" :min="1" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="allocDialog.visible = false">取消</el-button>
        <el-button type="warning" @click="submitAllocation" :loading="submitting">确认调拨</el-button>
      </template>
    </el-dialog>

  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const userRole = localStorage.getItem('role') || ''
const userDb = localStorage.getItem('db_name') || 'mysql'
const canSwitchDb = computed(() => userRole === 'super_admin')
const selectedDb = ref(canSwitchDb.value ? 'mssql' : userDb)

const medicines = ref([])
const inventoryMap = ref({})
const loading = ref(false)
const submitting = ref(false)

// 购物车数据
const cart = ref([])

const prescribeDialog = ref({ visible: false, patientName: '' })
const allocDialog = ref({ 
  visible: false, 
  medicineId: 0, 
  medicineName: '', 
  sourceBranchId: 3, // 默认源为总库
  targetBranchId: 1, 
  quantity: 10 
})

const dbNames = { 'mysql': '第一分院 (MySQL)', 'pg': '第二分院 (PostgreSQL)', 'mssql': '集团总院 (SQL Server)' }
const currentDbName = computed(() => dbNames[selectedDb.value])

const mergedData = computed(() => {
  return medicines.value.map(med => ({
    ...med,
    quantity: inventoryMap.value[med.id] || 0
  }))
})

const cartTotal = computed(() => {
  return cart.value.reduce((sum, item) => sum + item.price * item.count, 0)
})

const getRiskTagType = (level) => {
  if (level.includes('急救')) return 'danger'
  if (level === '处方药') return 'warning'
  return 'success'
}

const fetchData = async () => {
  loading.value = true
  try {
    const resMed = await axios.get(`http://127.0.0.1:8000/medicines/${selectedDb.value}`)
    medicines.value = resMed.data
    const resInv = await axios.get(`http://127.0.0.1:8000/business/stock/${selectedDb.value}`)
    const map = {}
    resInv.data.forEach(item => { map[item.medicine_id] = item.quantity })
    inventoryMap.value = map
  } catch (error) {
    ElMessage.error('数据加载失败')
  } finally {
    loading.value = false
  }
}

// 加入清单
const addToCart = (row) => {
  if (row.quantity <= 0) return ElMessage.warning('库存不足')
  
  const existingItem = cart.value.find(item => item.id === row.id)
  if (existingItem) {
    if (existingItem.count < row.quantity) {
      existingItem.count++
    } else {
      ElMessage.warning('已达到最大库存限制')
    }
  } else {
    cart.value.push({
      id: row.id,
      name: row.name,
      price: row.price,
      count: 1,
      maxStock: row.quantity
    })
  }
}

const removeFromCart = (index) => {
  cart.value.splice(index, 1)
}

const openPrescribeDialog = () => {
  if (cart.value.length === 0) return ElMessage.warning('请先选择药品')
  prescribeDialog.value.visible = true
}

// 提交处方
const submitPrescription = async () => {
  if (!prescribeDialog.value.patientName) return ElMessage.warning('请输入病人姓名')
  
  submitting.value = true
  try {
    const token = localStorage.getItem('token')
    
    const itemsPayload = cart.value.map(item => ({
      medicine_id: item.id,
      quantity: item.count
    }))

    const payload = {
      patient_name: prescribeDialog.value.patientName,
      items: itemsPayload
    }
    
    await axios.post('http://127.0.0.1:8000/business/prescription/create', payload, {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    ElMessage.success('处方开具成功！')
    prescribeDialog.value.visible = false
    cart.value = [] // 清空购物车
    fetchData() // 刷新库存
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '开药失败')
  } finally {
    submitting.value = false
  }
}

// 打开调拨弹窗
const openAllocationDialog = (row) => {
  allocDialog.value = { 
    visible: true, 
    medicineId: row.id, 
    medicineName: row.name, 
    sourceBranchId: 3, 
    targetBranchId: 1, 
    quantity: 10 
  }
}

// 提交调拨
const submitAllocation = async () => {
  if(allocDialog.value.sourceBranchId === allocDialog.value.targetBranchId) {
    return ElMessage.warning('源仓库和目标仓库不能相同')
  }

  submitting.value = true
  try {
    const token = localStorage.getItem('token')
    await axios.post('http://127.0.0.1:8000/business/allocation/create', {
      medicine_id: allocDialog.value.medicineId,
      source_branch_id: allocDialog.value.sourceBranchId, // 新增参数
      target_branch_id: allocDialog.value.targetBranchId,
      quantity: allocDialog.value.quantity
    }, { headers: { Authorization: `Bearer ${token}` } })
    
    ElMessage.success('调拨指令已发出，请留意冲突监控')
    allocDialog.value.visible = false
    fetchData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '调拨失败')
  } finally {
    submitting.value = false
  }
}

onMounted(fetchData)
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
.title-box { display: flex; align-items: center; }
.ml-2 { margin-left: 10px; }
.low-stock { color: red; font-weight: bold; }

/* 购物车样式 */
.cart-card { min-height: 400px; border-left: 1px solid #EBEEF5; }
.cart-item { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px dashed #eee; }
.item-info { flex: 1; }
.item-name { font-weight: bold; font-size: 14px; }
.item-price { color: #909399; font-size: 12px; }
.cart-footer { margin-top: 20px; text-align: right; }
.total-price { font-size: 16px; margin-bottom: 15px; }
.total-price span { color: #F56C6C; font-weight: bold; font-size: 20px; }
.submit-btn { width: 100%; }
.dialog-item { display: flex; justify-content: space-between; padding: 5px 0; }
.dialog-total { text-align: right; font-size: 18px; color: #F56C6C; font-weight: bold; margin-top: 10px; }
</style>