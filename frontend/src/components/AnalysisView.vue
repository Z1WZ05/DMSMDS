<template>
  <div class="analysis-page">
    <el-card class="filter-bar">
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        value-format="YYYY-MM-DD"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
      />
      <el-button type="primary" icon="Search" @click="fetchStats" style="margin-left:20px">执行多维分析</el-button>
    </el-card>

    <el-tabs tab-position="right" v-model="activeTab" class="main-tabs" @tab-change="handleTabChange">
      
      <el-tab-pane name="overview" label="📊 运营概览">
        <div class="full-pane" v-if="activeTab === 'overview'">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-card class="stat-box blue">
                <div class="tit">累计开方量</div>
                <div class="num">{{ summary.count }} <small>单</small></div>
              </el-card>
            </el-col>
            <el-col :span="12">
              <el-card class="stat-box green">
                <div class="tit">累计营收金额</div>
                <div class="num">¥ {{ summary.money.toFixed(2) }}</div>
              </el-card>
            </el-col>
          </el-row>
          <el-row :gutter="20" style="margin-top: 20px;">
            <el-col :span="14">
              <el-card header="各院区营收对比">
                <div id="branchChart" class="big-chart"></div>
              </el-card>
            </el-col>
            <el-col :span="10">
              <el-table :data="branchSales" border height="400">
                <el-table-column prop="name" label="院区" />
                <el-table-column prop="value" label="营收额(元)" />
              </el-table>
            </el-col>
          </el-row>
        </div>
      </el-tab-pane>

      <el-tab-pane name="trend" label="📈 营收趋势">
        <div class="full-pane" v-if="activeTab === 'trend'">
          <el-card header="每日营业额走势">
            <div id="lineChart" class="huge-chart"></div>
          </el-card>
        </div>
      </el-tab-pane>

      <el-tab-pane name="structure" label="🍕 药品结构">
        <div class="full-pane flex-pane" v-if="activeTab === 'structure'">
          <div class="chart-half" id="pieChart"></div>
          <div class="table-half">
            <el-table :data="tableData" border stripe height="100%">
              <el-table-column prop="medicine" label="药品" />
              <el-table-column prop="money" label="销售额" sortable />
            </el-table>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane name="ranking" label="🏆 销量排行">
        <div class="full-pane flex-pane" v-if="activeTab === 'ranking'">
          <div class="chart-half" id="barChart"></div>
          <div class="table-half">
            <el-table :data="tableData" border stripe height="100%">
              <el-table-column type="index" label="排名" />
              <el-table-column prop="medicine" label="药品名称" />
              <el-table-column prop="qty" label="销售总量" />
            </el-table>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane name="sync" label="🧬 同步健康度">
        <div class="full-pane" v-if="activeTab === 'sync'">
          <el-row :gutter="20">
            <el-col :span="16">
              <div id="syncChart" style="width: 100%; height: 550px"></div>
            </el-col>
            <el-col :span="8">
              <h3>同步明细表</h3>
              <el-table :data="syncTableData" border size="small">
                <el-table-column prop="sync_date" label="日期" width="100" />
                <el-table-column prop="auto_sync_count" label="自动" />
                <el-table-column prop="conflict_count" label="冲突" />
                <el-table-column prop="manual_resolve_count" label="人工" />
              </el-table>
            </el-col>
          </el-row>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const activeTab = ref('overview')
const dateRange = ref(['2025-01-01', '2025-12-31'])
const summary = ref({ count: 0, money: 0 })
const branchSales = ref([])
const tableData = ref([])
const lineData = ref({ dates: [], values: [] })
const pieData = ref([])
const syncTableData = ref([])

let activeCharts = []

// 清理旧图表，防止内存泄漏
const clearCharts = () => {
  activeCharts.forEach(c => c.dispose())
  activeCharts = []
}

const handleTabChange = () => {
  nextTick(() => renderCurrentTabCharts())
}

const renderCurrentTabCharts = () => {
  clearCharts()
  const commonGrid = { left: '3%', right: '4%', bottom: '3%', containLabel: true }

  if (activeTab.value === 'overview') {
    const dom = document.getElementById('branchChart')
    if (!dom) return
    const c = echarts.init(dom)
    c.setOption({
      tooltip: { trigger: 'axis' },
      grid: commonGrid,
      xAxis: { type: 'category', data: branchSales.value.map(i => i.name) },
      yAxis: { type: 'value' },
      series: [{ data: branchSales.value.map(i => i.value), type: 'bar', itemStyle: {color: '#409EFF'} }]
    })
    activeCharts.push(c)
  } 
  
  else if (activeTab.value === 'sync') {
    const dom = document.getElementById('syncChart')
    if (!dom) return
    const c = echarts.init(dom)
    c.setOption({
      title: { text: '系统同步趋势' },
      tooltip: { trigger: 'axis' },
      grid: commonGrid,
      legend: { data: ['自动广播', '冲突报警', '人工解决'], bottom: 0 },
      xAxis: { type: 'category', data: syncTableData.value.map(i => i.sync_date) },
      yAxis: { type: 'value' },
      series: [
        { name: '自动广播', type: 'line', data: syncTableData.value.map(i => i.auto_sync_count), smooth: true, color: '#67C23A' },
        { name: '冲突报警', type: 'bar', data: syncTableData.value.map(i => i.conflict_count), color: '#F56C6C' },
        { name: '人工解决', type: 'bar', data: syncTableData.value.map(i => i.manual_resolve_count), color: '#409EFF' }
      ]
    })
    activeCharts.push(c)
  }

  else if (activeTab.value === 'trend') {
    const dom = document.getElementById('lineChart')
    if (!dom) return
    const c = echarts.init(dom)
    c.setOption({
      grid: commonGrid,
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: lineData.value.dates },
      yAxis: { type: 'value' },
      series: [{ data: lineData.value.values, type: 'line', smooth: true, areaStyle: {opacity: 0.1} }]
    })
    activeCharts.push(c)
  }

  else if (activeTab.value === 'structure') {
    const dom = document.getElementById('pieChart')
    if (!dom) return
    const c = echarts.init(dom)
    c.setOption({
      title: { text: '营收贡献占比', left: 'center' },
      tooltip: { trigger: 'item' },
      series: [{ type: 'pie', radius: '60%', data: pieData.value, label: {show: true} }]
    })
    activeCharts.push(c)
  }

  else if (activeTab.value === 'ranking') {
    const dom = document.getElementById('barChart')
    if (!dom) return
    const c = echarts.init(dom)
    c.setOption({
      grid: { left: '150px', right: '50px', bottom: '30px' },
      xAxis: { type: 'value' },
      yAxis: { type: 'category', data: tableData.value.map(i => i.medicine).reverse() },
      series: [{ data: tableData.value.map(i => i.qty).reverse(), type: 'bar', itemStyle: {color: '#E6A23C'} }]
    })
    activeCharts.push(c)
  }
}

const fetchStats = async () => {
  try {
    const token = localStorage.getItem('token')
    const headers = { Authorization: `Bearer ${token}` }
    
    // 1. 获取主报表数据
    const res = await axios.get('http://127.0.0.1:8000/stats/dashboard', {
      params: { start_date: dateRange.value[0], end_date: dateRange.value[1] },
      headers
    })
    const data = res.data
    summary.value = data.summary
    branchSales.value = data.branch_sales
    tableData.value = data.table
    lineData.value = data.line
    pieData.value = data.pie

    // 2. 获取同步报表数据 (仅超管可见)
    if (localStorage.getItem('role') === 'super_admin') {
        const resSync = await axios.get('http://127.0.0.1:8000/stats/sync-report', { headers })
        syncTableData.value = resSync.data
    }

    nextTick(() => renderCurrentTabCharts())
  } catch (e) {
    ElMessage.error('报表加载失败，请检查后端连接')
  }
}

// 窗口缩放自适应
const handleResize = () => {
    activeCharts.forEach(c => c.resize())
}

onMounted(() => {
    fetchStats()
    window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
    window.removeEventListener('resize', handleResize)
    clearCharts()
})
</script>

<style scoped>
.analysis-page { height: calc(100vh - 100px); display: flex; flex-direction: column; padding: 20px; background: #f5f7fa; overflow: hidden; }
.filter-bar { margin-bottom: 20px; }
.main-tabs { flex: 1; background: white; border-radius: 8px; box-shadow: 0 2px 12px 0 rgba(0,0,0,0.1); overflow: hidden; }
.full-pane { padding: 30px; height: 100%; box-sizing: border-box; overflow-y: auto; }
.flex-pane { display: flex; gap: 20px; height: 600px; }
.chart-half { flex: 1.2; height: 100%; }
.table-half { flex: 0.8; height: 100%; }
.big-chart { width: 100%; height: 400px; }
.huge-chart { width: 100%; height: 600px; }
.stat-box { text-align: center; color: white; border-radius: 12px; }
.stat-box.blue { background: linear-gradient(135deg, #1890ff, #36cfc9); }
.stat-box.green { background: linear-gradient(135deg, #52c41a, #b7eb8f); }
.num { font-size: 36px; font-weight: bold; margin-top: 10px; }
:deep(.el-tabs__content) { height: 100%; }
:deep(.el-tabs__item) { height: 70px; font-size: 15px; font-weight: bold; }
</style>