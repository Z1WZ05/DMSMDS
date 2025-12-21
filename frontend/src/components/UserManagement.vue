<template>
  <el-card>
    <template #header>
      <div class="card-header">
        <span>👥 用户权限管理</span>
        <el-button type="primary" @click="showAddDialog = true">新增用户</el-button>
      </div>
    </template>

    <el-table :data="users" border stripe v-loading="loading">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="username" label="用户名" />
      <el-table-column prop="role" label="当前角色">
        <template #default="scope">
          <el-tag :type="getRoleTag(scope.row.role)">{{ scope.row.role }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="branch_id" label="所属分院">
        <template #default="scope">
          {{ getBranchName(scope.row.branch_id) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="scope">
          <el-button size="small" type="primary" @click="handleEdit(scope.row)">编辑</el-button>
          
          <!-- 【修改点】新增删除按钮，带二次确认 -->
          <el-popconfirm 
            title="确定要删除该用户吗？此操作不可恢复。" 
            confirm-button-text="确认删除"
            cancel-button-text="取消"
            @confirm="handleDelete(scope.row.id)"
          >
            <template #reference>
              <el-button size="small" type="danger">删除</el-button>
            </template>
          </el-popconfirm>

        </template>
      </el-table-column>
    </el-table>

    <!-- 弹窗 (新增/编辑) -->
    <el-dialog v-model="showAddDialog" :title="isEdit ? '编辑用户' : '创建新用户'" width="500px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="用户名" v-if="!isEdit">
          <el-input v-model="form.username" placeholder="登录账号" />
        </el-form-item>
        <!-- 编辑模式下用户名不可改 -->
        <el-form-item label="用户名" v-else>
          <el-input v-model="form.username" disabled />
        </el-form-item>
        
        <el-form-item label="密码" v-if="!isEdit">
          <el-input v-model="form.password" show-password placeholder="初始密码" />
        </el-form-item>
        
        <el-form-item label="角色">
          <el-select v-model="form.role" placeholder="选择角色">
            <el-option label="护士 (Nurse)" value="nurse" />
            <el-option label="医生 (Doctor)" value="doctor" />
            <el-option label="急诊医生 (Emergency)" value="emergency" />
            <el-option label="分院管理员 (Branch Admin)" value="branch_admin" />
          </el-select>
        </el-form-item>
        <el-form-item label="所属分院">
          <el-select v-model="form.branch_id" placeholder="选择分院">
            <el-option label="分院1 (MySQL)" :value="1" />
            <el-option label="分院2 (PG)" :value="2" />
            <el-option label="总院 (MSSQL)" :value="3" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const users = ref([])
const loading = ref(false)
const showAddDialog = ref(false)
const isEdit = ref(false)
const form = ref({ id: null, username: '', password: '', role: '', branch_id: 1 })

const getRoleTag = (role) => {
  if (role.includes('admin')) return 'danger'
  if (role === 'nurse') return 'success'
  return 'primary'
}

const getBranchName = (id) => {
  const map = { 1: '分院1 (MySQL)', 2: '分院2 (PG)', 3: '总院 (MSSQL)' }
  return map[id] || `未知(${id})`
}

const fetchUsers = async () => {
  loading.value = true
  try {
    const token = localStorage.getItem('token')
    const res = await axios.get('http://127.0.0.1:8000/users/', {
      headers: { Authorization: `Bearer ${token}` }
    })
    users.value = res.data
  } catch (e) {
    ElMessage.error('无法获取用户列表：权限不足或网络错误')
  } finally {
    loading.value = false
  }
}

const openCreate = () => {
  isEdit.value = false
  form.value = { username: '', password: '', role: '', branch_id: 1 }
  showAddDialog.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  // 复制对象，防止直接修改表格显示
  form.value = { 
    id: row.id,
    username: row.username,
    role: row.role,
    branch_id: row.branch_id,
    password: '' // 编辑模式不显示密码
  }
  showAddDialog.value = true
}

// 【修改点】提交表单（新增或更新）
const submitForm = async () => {
  const token = localStorage.getItem('token')
  try {
    if (isEdit.value) {
      // 编辑逻辑
      await axios.put(`http://127.0.0.1:8000/users/${form.value.id}`, {
        role: form.value.role,
        branch_id: form.value.branch_id
      }, {
        headers: { Authorization: `Bearer ${token}` }
      })
      ElMessage.success('用户权限修改成功')
    } else {
      // 新增逻辑
      if (!form.value.username || !form.value.password) return ElMessage.warning('请填写完整')
      await axios.post('http://127.0.0.1:8000/users/', form.value, {
        headers: { Authorization: `Bearer ${token}` }
      })
      ElMessage.success('用户创建成功')
    }
    showAddDialog.value = false
    fetchUsers()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

// 【修改点】删除用户
const handleDelete = async (userId) => {
  try {
    const token = localStorage.getItem('token')
    await axios.delete(`http://127.0.0.1:8000/users/${userId}`, {
        headers: { Authorization: `Bearer ${token}` }
    })
    ElMessage.success('用户已删除')
    fetchUsers() // 刷新列表
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

onMounted(fetchUsers)
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>