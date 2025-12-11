<template>
  <el-row :gutter="20">
    <el-col :span="24">
      <el-card>
        <template #header>📊 医疗物资价值分布 (各分院)</template>
        <div id="chart" style="width: 100%; height: 400px;"></div>
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup>
import { onMounted } from 'vue'
import * as echarts from 'echarts'
import axios from 'axios'

const initChart = async () => {
  const chartDom = document.getElementById('chart')
  // 防止重复初始化
  if (echarts.getInstanceByDom(chartDom)) return;
  
  const myChart = echarts.init(chartDom)
  
  try {
    // 默认查询抗生素类
    const res = await axios.get('http://127.0.0.1:8000/analysis/inventory-value?category=抗生素')
    const data = res.data
    
    const option = {
      title: { text: '抗生素类药品总库存价值' },
      tooltip: {},
      xAxis: {
        type: 'category',
        data: data.map(item => item.warehouse_name)
      },
      yAxis: { type: 'value' },
      series: [
        {
          data: data.map(item => item.total_value),
          type: 'bar',
          itemStyle: { color: '#409EFF' },
          label: { show: true, position: 'top' }
        }
      ]
    }
    
    myChart.setOption(option)
  } catch (e) {
    console.error("加载图表失败", e)
  }
}

onMounted(initChart)
</script>