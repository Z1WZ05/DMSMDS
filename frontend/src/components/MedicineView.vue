<template>
  <div class="medicine-view">
    <el-row :gutter="20">
      <!-- 左侧：药品列表区域 (占 16/24 宽度) -->
      <el-col :span="userRole.includes('admin') ? 24 : 16">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <div class="title-box">
                <el-icon><Menu /></el-icon>
                <span class="title-text">药品库存实时总览</span>
                <el-tag v-if="!canSwitchDb" type="info" class="ml-2" effect="plain">
                  当前院区: {{ currentDbName }}
                </el-tag>
              </div>
              
              <!-- 只有超级管理员(super_admin)才能切换查看其他院区的数据库副本 -->
              <el-select 
                v-if="canSwitchDb" 
                v-model="selectedDb" 
                placeholder="切换院区视图" 
                @change="fetchData" 
                style="width: 220px;">
                <template #prefix>
                  <el-icon><Monitor /></el-icon>
                </template>
                <el-option label="第一分院 (MySQL)" value="mysql" />
                <el-option label="第二分院 (PostgreSQL)" value="pg" />
                <el-option label="集团总院 (SQL Server)" value="mssql" />
              </el-select>
            </div>
          </template>

          <!-- 药品信息与库存合并表格 -->
          <el-table :data="mergedData" stripe style="width: 100%" v-loading="loading" border>
            <el-table-column prop="id" label="ID" width="70" align="center" />
            <el-table-column prop="name" label="药品名称" min-width="150" />
            <el-table-column prop="category" label="分类" width="100" align="center" />
            <el-table-column prop="price" label="单价(元)" width="100" align="right">
              <template #default="scope">¥{{ scope.row.price.toFixed(2) }}</template>
            </el-table-column>
            
            <el-table-column prop="quantity" label="当前库存" width="120" align="center">
              <template #default="scope">
                <b :class="{'low-stock-text': scope.row.quantity < 20}">{{ scope.row.quantity }}</b>
                <el-tag size="small" type="danger" v-if="scope.row.quantity < 20" style="margin-left: 5px">紧缺</el-tag>
              </template>
            </el-table-column>

            <el-table-column prop="danger_level" label="管控等级" width="130" align="center">
              <template #default="scope">
                <el-tag :type="getRiskTagType(scope.row.danger_level)" effect="light">
                  {{ scope.row.danger_level }}
                </el-tag>
              </template>
            </el-table-column>
            
            <el-table-column label="业务操作" min-width="220" fixed="right">
              <template #default="scope">
                 <!-- 1. 医护端功能：加入处方清单 -->
                 <el-button 
                   v-if="!userRole.includes('admin')" 
                   type="primary" size="small" 
                   @click="addToCart(scope.row)">
                   <el-icon><Plus /></el-icon> 加入处方
                 </el-button>
                 
                 <!-- 2. 超管端功能：仅在总院视图(mssql)下显示调配与入库 -->
                 <template v-if="userRole === 'super_admin' && selectedDb === 'mssql'">
                   <el-button 
                     type="warning" size="small" icon="Connection"
                     @click="openAllocationDialog(scope.row)">
                     调配
                   </el-button>
                   <el-button 
                     type="success" size="small" plain icon="Box"
                     @click="openInboundDialog(scope.row)">
                     入库
                   </el-button>
                 </template>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- 右侧：处方清单篮 (仅医护人员可见) -->
      <el-col :span="8" v-if="!userRole.includes('admin')">
        <el-card class="cart-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span><el-icon><Notebook /></el-icon> 待开处方清单</span>
              <el-tag type="warning" effect="dark" round>{{ cart.length }}</el-tag>
            </div>
          </template>

          <div v-if="cart.length === 0" class="empty-cart">
            <el-empty description="请从左侧添加药品" :image-size="100" />
          </div>

          <div v-else class="cart-content">
            <div v-for="(item, index) in cart" :key="item.id" class="cart-item">
              <div class="item-main">
                <div class="item-name">{{ item.name }}</div>
                <div class="item-sub">单价: ¥{{ item.price }} | 库存: {{ item.maxStock }}</div>
              </div>
              <div class="item-ctrl">
                <el-input-number v-model="item.count" :min="1" :max="item.maxStock" size="small" style="width: 90px" />
                <el-button type="danger" link icon="Delete" @click="removeFromCart(index)" style="margin-left: 10px"></el-button>
              </div>
            </div>

            <div class="cart-footer">
              <div class="total-row">
                <span>处方预计金额:</span>
                <span class="total-val">¥{{ cartTotal.toFixed(2) }}</span>
              </div>
              <el-button type="primary" class="submit-btn" @click="prescribeDialog.visible = true" size="large">
                生成处方并结算扣库
              </el-button>
              <el-button type="info" link @click="cart = []" style="width: 100%; margin-top: 10px">清空清单</el-button>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- ========================================== -->
    <!-- 弹窗集 (Dialogs) -->
    <!-- ========================================== -->

    <!-- 1. 处方确认弹窗 -->
    <el-dialog v-model="prescribeDialog.visible" title="📋 处方最终确认" width="450px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="病人姓名" required>
          <el-input v-model="prescribeDialog.patientName" placeholder="请录入患者姓名" />
        </el-form-item>
        <div class="dialog-detail">
          <p class="detail-title">药品明细：</p>
          <div v-for="item in cart" :key="item.id" class="detail-row">
            <span>{{ item.name }}</span>
            <span>x {{ item.count }}</span>
          </div>
          <el-divider />
          <div class="detail-total">
            应付总额：<b>¥{{ cartTotal.toFixed(2) }}</b>
          </div>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="prescribeDialog.visible = false">返回修改</el-button>
        <el-button type="primary" @click="submitPrescription" :loading="submitting">确认提交 (跨库同步)</el-button>
      </template>
    </el-dialog>

    <!-- 2. 全网物资调拨弹窗 -->
    <el-dialog v-model="allocDialog.visible" title="🚚 全网物资调拨指令" width="480px">
      <el-form label-width="100px">
        <el-form-item label="调拨药品">
          <el-input v-model="allocDialog.medicine_name" disabled />
        </el-form-item>
        <el-form-item label="发货方(源)">
          <el-select v-model="allocDialog.source_branch_id" style="width: 100%">
            <el-option label="第一分院 (MySQL)" :value="1" />
            <el-option label="第二分院 (PostgreSQL)" :value="2" />
            <el-option label="集团总库 (MSSQL)" :value="3" />
          </el-select>
        </el-form-item>
        <el-form-item label="接收方(目标)">
          <el-select v-model="allocDialog.target_branch_id" style="width: 100%">
            <el-option label="第一分院 (MySQL)" :value="1" />
            <el-option label="第二分院 (PostgreSQL)" :value="2" />
            <el-option label="集团总库 (MSSQL)" :value="3" />
          </el-select>
        </el-form-item>
        <el-form-item label="调拨数量">
          <el-input-number v-model="allocDialog.quantity" :min="1" style="width: 100%" />
        </el-form-item>
        <el-alert title="注意：此操作将直接修改总院记录的时间戳，触发全网冲突报警，需管理员人工仲裁。" type="warning" :closable="false" show-icon />
      </el-form>
      <template #footer>
        <el-button @click="allocDialog.visible = false">取消</el-button>
        <el-button type="warning" @click="submitAllocation" :loading="submitting">下达调拨指令</el-button>
      </template>
    </el-dialog>

    <!-- 3. 集团物资入库弹窗 -->
    <el-dialog v-model="inboundDialog.visible" title="📦 集团物资采购入库" width="400px">
      <el-form label-width="100px">
        <el-form-item label="入库药品">
          <el-input v-model="inboundDialog.medicine_name" disabled />
        </el-form-item>
        <el-form-item label="入库院区">
          <el-select v-model="inboundDialog.warehouse_id" style="width: 100%">
            <el-option label="第一分院 (MySQL)" :value="1" />
            <el-option label="第二分院 (PostgreSQL)" :value="2" />
            <el-option label="集团总库 (MSSQL)" :value="3" />
          </el-select>
        </el-form-item>
        <el-form-item label="入库数量">
          <el-input-number v-model="inboundDialog.quantity" :min="1" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="inboundDialog.visible = false">取消</el-button>
        <el-button type="success" @click="submitInbound" :loading="submitting">确认入库并记账</el-button>
      </template>
    </el-dialog>

  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete, Menu, Monitor, Notebook } from '@element-plus/icons-vue'

// --- 用户状态与权限控制 ---
const userRole = localStorage.getItem('role') || ''
const userDb = localStorage.getItem('db_name') || 'mysql'
const canSwitchDb = computed(() => userRole === 'super_admin')
// 如果是普通医生，selectedDb 永远锁定在自己的 db；如果是超管，默认看 mssql
const selectedDb = ref(canSwitchDb.value ? 'mssql' : userDb)

const dbNames = { 
  'mysql': '第一分院 (MySQL)', 
  'pg': '第二分院 (PostgreSQL)', 
  'mssql': '集团总院 (SQL Server)' 
}
const currentDbName = computed(() => dbNames[selectedDb.value])

// --- 基础状态变量 ---
const medicines = ref([])
const inventoryMap = ref({})
const loading = ref(false)
const submitting = ref(false)

// --- 处方购物车逻辑 ---
const cart = ref([])
const cartTotal = computed(() => {
  return cart.value.reduce((sum, item) => sum + item.price * item.count, 0)
})

// --- 弹窗对象定义 ---
const prescribeDialog = ref({ visible: false, patientName: '' })
const allocDialog = ref({ 
  visible: false, medicine_id: 0, medicine_name: '', 
  source_branch_id: 3, target_branch_id: 1, quantity: 10 
})
const inboundDialog = ref({ 
  visible: false, medicine_id: 0, medicine_name: '', 
  warehouse_id: 3, quantity: 100 
})

// --- 合并库存数据到药品列表 ---
const mergedData = computed(() => {
  return medicines.value.map(med => ({
    ...med,
    quantity: inventoryMap.value[med.id] || 0
  }))
})

// --- 辅助：危险等级标签颜色 ---
const getRiskTagType = (level) => {
  if (level.includes('急救')) return 'danger'
  if (level === '处方药') return 'warning'
  return 'success'
}

// --- 方法：从后端拉取全量数据 ---
const fetchData = async () => {
  loading.value = true
  try {
    const token = localStorage.getItem('token')
    const headers = { Authorization: `Bearer ${token}` }
    
    const [resMed, resInv] = await Promise.all([
      axios.get(`http://127.0.0.1:8000/medicines/${selectedDb.value}`, { headers }),
      axios.get(`http://127.0.0.1:8000/business/stock/${selectedDb.value}`, { headers })
    ])
    
    medicines.value = resMed.data
    const map = {}
    resInv.data.forEach(item => { map[item.medicine_id] = item.quantity })
    inventoryMap.value = map
  } catch (error) {
    console.error(error)
    ElMessage.error('库存同步状态获取失败，请检查数据库连接')
  } finally {
    loading.value = false
  }
}

// --- 购物车操作 ---
const addToCart = (row) => {
  if (row.quantity <= 0) {
    return ElMessage.error('当前院区该药品已断货，请联系管理部调配')
  }
  
  const existingItem = cart.value.find(item => item.id === row.id)
  if (existingItem) {
    if (existingItem.count < row.quantity) {
      existingItem.count++
    } else {
      ElMessage.warning('已达到当前最大库存量')
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

// --- 业务提交方法 ---

// 1. 提交处方结算 (核心业务)
const submitPrescription = async () => {
  if (!prescribeDialog.value.patientName) return ElMessage.warning('必须录入患者姓名')
  
  submitting.value = true
  try {
    const token = localStorage.getItem('token')
    const payload = {
      patient_name: prescribeDialog.value.patientName,
      items: cart.value.map(item => ({ 
        medicine_id: item.id, 
        quantity: item.count 
      }))
    }

    if (cartTotal.value > 2000) {
      try {
          await ElMessageBox.confirm(
              `当前处方金额 (¥${cartTotal.value.toFixed(2)}) 已触发系统自动审计阈值。开具该处方将被数据库触发器实时记录在案。是否确认开具？`,
              '高额处方风险警告',
              {
                  confirmButtonText: '本人确认并开具',
                  cancelButtonText: '返回修改',
                  type: 'error',
                  center: true
              }
          )
      } catch {
          return; // 用户取消，直接返回
      }
  }
    
    await axios.post('http://127.0.0.1:8000/business/prescription/create', payload, {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    ElMessage.success('处方已成功下达并完成库存扣减')
    prescribeDialog.value.visible = false
    prescribeDialog.value.patientName = ''
    cart.value = [] // 结算后清空购物车
    fetchData() // 刷新本地库存
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '处方提交失败，请检查权限或库存')
  } finally {
    submitting.value = false
  }
}

// 2. 提交调拨指令 (超管)
const openAllocationDialog = (row) => {
  allocDialog.value = { 
    visible: true, medicine_id: row.id, medicine_name: row.name, 
    source_branch_id: 3, target_branch_id: 1, quantity: 10 
  }
}

const submitAllocation = async () => {
  if (allocDialog.value.source_branch_id === allocDialog.value.target_branch_id) {
    return ElMessage.warning('源仓和目标仓不能相同')
  }
  
  submitting.value = true
  try {
    const token = localStorage.getItem('token')
    await axios.post('http://127.0.0.1:8000/business/allocation/create', allocDialog.value, {
      headers: { Authorization: `Bearer ${token}` }
    })
    ElMessage.success('调拨指令已发出，请观察同步报警列表')
    allocDialog.value.visible = false
    fetchData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '调拨失败')
  } finally {
    submitting.value = false
  }
}

// 3. 提交采购入库 (超管)
const openInboundDialog = (row) => {
  inboundDialog.value = { 
    visible: true, medicine_id: row.id, medicine_name: row.name, 
    warehouse_id: 3, quantity: 100 
  }
}

const submitInbound = async () => {
  submitting.value = true
  try {
    const token = localStorage.getItem('token')
    await axios.post('http://127.0.0.1:8000/business/inbound/create', inboundDialog.value, {
      headers: { Authorization: `Bearer ${token}` }
    })
    ElMessage.success('入库登记成功')
    inboundDialog.value.visible = false
    fetchData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '入库失败')
  } finally {
    submitting.value = false
  }
}

onMounted(fetchData)
</script>

<style scoped>
.medicine-view { padding: 10px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.title-box { display: flex; align-items: center; font-size: 16px; }
.title-text { margin-left: 8px; font-weight: bold; }
.ml-2 { margin-left: 10px; }
.low-stock-text { color: #F56C6C; }

/* 购物车样式 */
.cart-card { min-height: 550px; background-color: #fafafa; }
.empty-cart { padding-top: 80px; }
.cart-content { display: flex; flex-direction: column; height: 450px; }
.cart-item { 
  display: flex; 
  justify-content: space-between; 
  align-items: center; 
  padding: 15px 0; 
  border-bottom: 1px dashed #dcdfe6; 
}
.item-main { flex: 1; }
.item-name { font-weight: bold; font-size: 15px; color: #303133; }
.item-sub { font-size: 12px; color: #909399; margin-top: 4px; }
.item-ctrl { display: flex; align-items: center; }

.cart-footer { margin-top: auto; padding-top: 20px; border-top: 2px solid #ebeef5; }
.total-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
.total-row span { font-size: 15px; color: #606266; }
.total-val { font-size: 24px !important; color: #F56C6C !important; font-weight: bold; }
.submit-btn { width: 100%; height: 50px; font-size: 16px; font-weight: bold; }

/* 弹窗明细样式 */
.dialog-item { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #f2f6fc; }
.dialog-total { text-align: right; font-size: 18px; color: #F56C6C; font-weight: bold; margin-top: 20px; }
</style>