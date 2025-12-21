<template>
  <el-container class="layout-container">
    <el-aside width="220px" class="aside">
      <div class="logo-box">
        <el-icon><FirstAidKit /></el-icon> 
        <span> 医疗物资系统</span>
      </div>
      
      <el-menu :default-active="activeTab" class="el-menu-vertical" @select="handleSelect" background-color="#001529" text-color="#fff" active-text-color="#409EFF">
        
        <el-menu-item index="1">
          <el-icon><Goods /></el-icon>
          <span>药品库存 / 开药</span>
        </el-menu-item>

        <!-- 【新增】处方管理 -->
        <el-menu-item index="6">
          <el-icon><Tickets /></el-icon>
          <span>处方记录管理</span>
        </el-menu-item>

        <el-menu-item index="2" v-if="isAdmin">
          <el-icon><Warning /></el-icon>
          <span>冲突监控与处理</span>
        </el-menu-item>

        <!-- 菜单部分 -->
        <el-menu-item index="3">
          <el-icon><Histogram /></el-icon>
          <span>业务统计看板</span>
        </el-menu-item>

        <el-menu-item index="7" v-if="role === 'super_admin'">
          <el-icon><Setting /></el-icon>
          <span>系统同步设置</span>
        </el-menu-item>

        <el-menu-item index="4" v-if="!isAdmin">
          <el-icon><List /></el-icon>
          <span>我的操作流水</span>
        </el-menu-item>

        <el-menu-item index="5" v-if="isAdmin">
          <el-icon><User /></el-icon>
          <span>系统用户管理</span>
        </el-menu-item>

        <!-- 菜单部分：新增管理员操作日志菜单 -->
        <el-menu-item index="8" v-if="role === 'super_admin'">
          <el-icon><DataBoard /></el-icon>
          <span>管理员审计日志</span>
        </el-menu-item>

        <el-menu-item index="9">
        <el-icon><Management /></el-icon>
          <span>系统高级中心</span>
        </el-menu-item>

        <el-menu-item index="10" v-if="isAdmin">
        <el-icon><Checked /></el-icon>
          <span>风险预警中心</span>
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
        <MedicineView v-if="activeTab === '1'" />
        <ConflictView v-if="activeTab === '2'" />
        <AnalysisView v-if="activeTab === '3'" />
        <MyRecordsView v-if="activeTab === '4'" />
        <UserManagement v-if="activeTab === '5'" />
        <PrescriptionList v-if="activeTab === '6'" />
        <SettingsView v-if="activeTab === '7'" />
        <AdminActionsView v-if="activeTab === '8'" />
        <AdvancedCenter v-if="activeTab === '9'" />
        <RiskCenter v-if="activeTab === '10'" /> 
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import MedicineView from '../components/MedicineView.vue'
import ConflictView from '../components/ConflictView.vue'
import AnalysisView from '../components/AnalysisView.vue'
import MyRecordsView from '../components/MyRecordsView.vue'
import UserManagement from '../components/UserManagement.vue'
import PrescriptionList from '../components/PrescriptionList.vue' // 引入新组件
import SettingsView from '../components/SettingsView.vue'
import AdminActionsView from '../components/AdminActionsView.vue'
import AdvancedCenter from '../components/AdvancedCenter.vue'
import RiskCenter from '../components/RiskCenter.vue' // 引入风险预警中心组件

const router = useRouter()
const activeTab = ref('1')
const username = localStorage.getItem('username')
const role = localStorage.getItem('role')

const isAdmin = computed(() => role && role.includes('admin'))

const titleMap = {
  '1': '药品库存管理',
  '2': '数据冲突处理中心',
  '3': '数据可视化分析',
  '4': '我的操作流水',
  '5': '系统用户权限管理',
  '6': '处方记录管理'
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