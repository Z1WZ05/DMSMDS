<template>
  <el-container class="layout-container">
    <el-aside width="220px" class="aside">
      <div class="logo-box">
        <el-icon><FirstAidKit /></el-icon> 
        <span> 医疗物资系统</span>
      </div>
      
      <el-menu :default-active="activeTab" class="el-menu-vertical" @select="handleSelect" background-color="#001529" text-color="#fff" active-text-color="#409EFF">
        
        <!-- 通用菜单 -->
        <el-menu-item index="1">
          <el-icon><Goods /></el-icon>
          <span>药品库存 / 开药</span>
        </el-menu-item>

        <!-- 仅管理员可见 -->
        <el-menu-item index="2" v-if="isAdmin">
          <el-icon><Warning /></el-icon>
          <span>冲突监控与处理</span>
        </el-menu-item>

        <el-menu-item index="3" v-if="isAdmin">
          <el-icon><DataLine /></el-icon>
          <span>全院数据报表</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="breadcrumb">当前位置：{{ currentTitle }}</div>
        <div class="user-info">
          <el-tag size="large" effect="dark">{{ role }}</el-tag>
          <span class="username">{{ username }}</span>
          <el-button type="danger" link @click="logout">退出</el-button>
        </div>
      </el-header>

      <el-main>
        <!-- 动态组件区域 -->
        <MedicineView v-if="activeTab === '1'" />
        <ConflictView v-if="activeTab === '2'" />
        <AnalysisView v-if="activeTab === '3'" />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
// 引入之前的组件
import MedicineView from '../components/MedicineView.vue'
import ConflictView from '../components/ConflictView.vue'
import AnalysisView from '../components/AnalysisView.vue'

const router = useRouter()
const activeTab = ref('1')
const username = localStorage.getItem('username')
const role = localStorage.getItem('role')

// 判断是否为管理员 (branch_admin 或 super_admin)
const isAdmin = computed(() => role.includes('admin'))

const titleMap = {
  '1': '药品库存管理',
  '2': '数据冲突处理中心',
  '3': '数据可视化分析'
}
const currentTitle = computed(() => titleMap[activeTab.value])

const handleSelect = (key) => {
  activeTab.value = key
}

const logout = () => {
  localStorage.clear()
  router.push('/login')
}
</script>

<style scoped>
.layout-container { height: 100vh; }
.aside { background-color: #001529; color: white; display: flex; flex-direction: column; }
.logo-box { height: 60px; display: flex; align-items: center; justify-content: center; font-size: 18px; font-weight: bold; border-bottom: 1px solid #002140; }
.el-menu-vertical { border-right: none; }
.header { background: #fff; border-bottom: 1px solid #dcdfe6; display: flex; align-items: center; justify-content: space-between; padding: 0 20px; }
.user-info { display: flex; align-items: center; gap: 15px; }
.username { font-weight: bold; color: #333; }
</style>