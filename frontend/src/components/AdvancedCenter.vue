<template>
  <div class="advanced-page">
    <el-tabs type="border-card">
      
      <!-- 维度 1: 性能挑战 (左右对比) -->
      <el-tab-pane label="🚀 性能挑战实验室">
        <div class="lab-header">
          <h3>大数据量复杂关联查询：索引优化对比</h3>
          <el-button type="danger" @click="runChallenge" :loading="loading">点击运行对比测试</el-button>
        </div>

        <el-row :gutter="20" style="margin-top: 20px" v-if="data">
          <el-col :span="12">
            <el-card header="🔴 无优化 (全表扫描)" class="perf-card unoptimized">
              <div class="time">{{ data.unoptimized.time }} <small>ms</small></div>
              <div class="explain-box">
                <p>执行计划：</p>
                <pre>{{ data.unoptimized.explain }}</pre>
              </div>
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card header="🟢 已优化 (利用复合索引)" class="perf-card optimized">
              <div class="time">{{ data.optimized.time }} <small>ms</small></div>
              <div class="explain-box">
                <p>执行计划：</p>
                <pre>{{ data.optimized.explain }}</pre>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>

      <!-- 维度 2: 游标应用 -->
      <el-tab-pane label="⚙️ 游标智能盘点">
        <div class="diag-container">
          <p>调用数据库内部游标，逐行分析库存周转率，生成智能补货报告。</p>
          <el-button type="primary" @click="doDiag" :loading="diagLoading">启动游标计算</el-button>
          <div v-if="report" class="report-view">
            <pre>{{ report }}</pre>
          </div>
        </div>
      </el-tab-pane>

    </el-tabs>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const diagLoading = ref(false)
const data = ref(null)
const report = ref('')

const runChallenge = async () => {
  loading.value = true
  try {
    const res = await axios.get('http://127.0.0.1:8000/advanced/performance-challenge', {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    data.value = res.data
  } finally {
    loading.value = false
  }
}

const doDiag = async () => {
  diagLoading.value = true
  try {
    const res = await axios.post('http://127.0.0.1:8000/advanced/inventory-diagnosis', {}, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    report.value = res.data.report
  } finally {
    diagLoading.value = false
  }
}
</script>

<style scoped>
.advanced-page { padding: 20px; }
.lab-header { text-align: center; margin-bottom: 30px; }
.perf-card { height: 500px; }
.time { font-size: 48px; font-weight: bold; text-align: center; margin: 20px 0; }
.unoptimized .time { color: #F56C6C; }
.optimized .time { color: #67C23A; }
.explain-box { background: #333; color: #fff; padding: 15px; height: 250px; overflow: auto; border-radius: 4px; font-size: 12px; }
.report-view { margin-top: 20px; padding: 20px; background: #fffbe6; border-left: 5px solid #e6a23c; }
</style>