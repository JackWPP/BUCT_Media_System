<template>
  <div class="dashboard-container">
    <n-spin :show="loading">
      <div class="stats-cards">
        <n-grid x-gap="12" :cols="3">
          <n-grid-item>
            <n-card title="总照片数">
              <n-statistic label="Photos">
                {{ stats?.total_photos || 0 }}
              </n-statistic>
            </n-card>
          </n-grid-item>
          <n-grid-item>
            <n-card title="总浏览量">
              <n-statistic label="Views">
                {{ stats?.total_views || 0 }}
              </n-statistic>
            </n-card>
          </n-grid-item>
          <n-grid-item>
            <n-card title="存储占用">
              <n-statistic label="Storage">
                {{ formatStorage(stats?.total_storage || 0) }}
              </n-statistic>
            </n-card>
          </n-grid-item>
        </n-grid>
      </div>

      <n-grid x-gap="12" y-gap="12" :cols="2" style="margin-top: 16px;">
        <n-grid-item>
          <n-card title="近30天上传趋势">
            <div class="chart-container">
              <v-chart class="chart" :option="uploadTrendOption" autoresize />
            </div>
          </n-card>
        </n-grid-item>
        <n-grid-item>
          <n-card title="热门标签">
            <div class="chart-container">
              <v-chart class="chart" :option="popularTagsOption" autoresize />
            </div>
          </n-card>
        </n-grid-item>
      </n-grid>

      <n-card title="热门照片 Top 10" style="margin-top: 16px;">
        <n-data-table
          :columns="columns"
          :data="stats?.top_photos || []"
          :bordered="false"
        />
      </n-card>
    </n-spin>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useMessage } from 'naive-ui'
import { getDashboardStats, type DashboardStats } from '../../api/stats'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, PieChart, LineChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
} from 'echarts/components'

use([
  CanvasRenderer,
  BarChart,
  PieChart,
  LineChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
])

const message = useMessage()
const loading = ref(false)
const stats = ref<DashboardStats | null>(null)

const columns = [
  { title: '文件名', key: 'filename' },
  { title: '浏览量', key: 'views' },
]

onMounted(() => {
  fetchStats()
})

async function fetchStats() {
  loading.value = true
  try {
    const data = await getDashboardStats() as unknown as DashboardStats
    stats.value = data
  } catch (error) {
    message.error('加载统计数据失败')
  } finally {
    loading.value = false
  }
}

const uploadTrendOption = computed(() => {
  if (!stats.value) return {}
  return {
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: stats.value.daily_uploads.map(d => d.date),
    },
    yAxis: { type: 'value' },
    series: [
      {
        data: stats.value.daily_uploads.map(d => d.count),
        type: 'line',
        smooth: true,
      },
    ],
  }
})

const popularTagsOption = computed(() => {
  if (!stats.value) return {}
  
  // Transform data for WordCloud-like Pie or simple Pie
  const data = stats.value.popular_tags.map(t => ({
      value: t.count,
      name: t.name
  }))

  return {
    tooltip: { trigger: 'item' },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: false,
          position: 'center'
        },
        data: data
      }
    ]
  }
})

function formatStorage(bytes: number) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}
</script>

<style scoped>
.dashboard-container {
  padding: 24px;
}
.chart-container {
  height: 300px;
}
.chart {
  height: 100%;
  width: 100%;
}
</style>
