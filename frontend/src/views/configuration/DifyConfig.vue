<template>
  <div class="dify-config-container">
    <div class="page-header">
      <h1>🤖 AI评测师配置</h1>
      <p>配置Dify API以启用AI评测师功能</p>
    </div>

    <div class="config-content">
      <el-card class="config-card">
        <template #header>
          <div class="card-header">
            <span>Dify API配置</span>
            <el-tag v-if="currentConfig" type="success">已配置</el-tag>
            <el-tag v-else type="info">未配置</el-tag>
          </div>
        </template>

        <el-form :model="form" :rules="rules" ref="configForm" label-width="120px">
          <el-form-item label="API URL" prop="api_url">
            <el-input
              v-model="form.api_url"
              placeholder="https://api.dify.ai/v1"
              clearable
            >
              <template #prepend>
                <el-icon><Link /></el-icon>
              </template>
            </el-input>
            <div class="form-tip">Dify API的完整URL地址</div>
          </el-form-item>

          <el-form-item label="API Key" prop="api_key">
            <el-input
              v-model="form.api_key"
              type="password"
              :placeholder="currentConfig ? '留空则不修改API Key' : '请输入API Key'"
              show-password
              clearable
            >
              <template #prepend>
                <el-icon><Key /></el-icon>
              </template>
            </el-input>
            <div class="form-tip">从Dify平台获取的API密钥</div>
          </el-form-item>

          <el-form-item label="启用状态" prop="is_active">
            <el-switch v-model="form.is_active" />
            <span class="switch-label">{{ form.is_active ? '已启用' : '已禁用' }}</span>
          </el-form-item>

          <el-form-item>
            <el-button type="primary" @click="testConnection" :loading="testing">
              <el-icon><Connection /></el-icon>
              测试连接
            </el-button>
            <el-button type="success" @click="saveConfig" :loading="saving">
              <el-icon><Check /></el-icon>
              保存配置
            </el-button>
            <el-button @click="resetForm">
              <el-icon><RefreshLeft /></el-icon>
              重置
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card class="info-card" v-if="currentConfig">
        <template #header>
          <span>当前配置信息</span>
        </template>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="API URL">
            {{ currentConfig.api_url }}
          </el-descriptions-item>
          <el-descriptions-item label="API Key">
            {{ currentConfig.api_key_masked || '****' }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="currentConfig.is_active ? 'success' : 'info'">
              {{ currentConfig.is_active ? '已启用' : '已禁用' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ formatDate(currentConfig.created_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="更新时间">
            {{ formatDate(currentConfig.updated_at) }}
          </el-descriptions-item>
        </el-descriptions>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Link, Key, Connection, Check, RefreshLeft } from '@element-plus/icons-vue'
import api from '@/utils/api'

const configForm = ref(null)
const currentConfig = ref(null)
const testing = ref(false)
const saving = ref(false)

const form = ref({
  api_url: '',
  api_key: '',
  is_active: true
})

const rules = {
  api_url: [
    { required: true, message: '请输入API URL', trigger: 'blur' },
    { type: 'url', message: '请输入有效的URL', trigger: 'blur' }
  ],
  api_key: [
    { min: 8, message: 'API Key长度至少8位', trigger: 'blur' }
  ]
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}

const loadConfig = async () => {
  try {
    const response = await api.get('/assistant/config/dify/')
    currentConfig.value = response.data
    form.value = {
      api_url: response.data.api_url,
      api_key: '', // Don't populate API key for security
      is_active: response.data.is_active
    }
  } catch (error) {
    if (error.response?.status !== 404) {
      console.error('加载配置失败:', error)
    }
  }
}

const testConnection = async () => {
  if (!configForm.value) return
  
  await configForm.value.validate(async (valid) => {
    if (!valid) return
    
    testing.value = true
    try {
      const response = await api.post('/assistant/config/dify/test_connection/', {
        api_url: form.value.api_url,
        api_key: form.value.api_key
      })
      
      if (response.data.success) {
        ElMessage.success('连接测试成功！')
      } else {
        ElMessage.error(response.data.error || '连接测试失败')
      }
    } catch (error) {
      console.error('测试连接失败:', error)
      ElMessage.error(error.response?.data?.error || '连接测试失败')
    } finally {
      testing.value = false
    }
  })
}

const saveConfig = async () => {
  if (!configForm.value) return
  
  await configForm.value.validate(async (valid) => {
    if (!valid) return
    
    saving.value = true
    try {
      // 准备要保存的数据
      const dataToSave = {
        api_url: form.value.api_url,
        is_active: form.value.is_active
      }
      
      // 只有当API Key有值时才发送（用户输入了新的API Key）
      if (form.value.api_key && form.value.api_key.trim()) {
        dataToSave.api_key = form.value.api_key
      }
      
      if (currentConfig.value) {
        // Update existing config
        await api.patch(`/assistant/config/dify/${currentConfig.value.id}/`, dataToSave)
        ElMessage.success('配置更新成功！')
      } else {
        // Create new config - API key is required
        if (!form.value.api_key || !form.value.api_key.trim()) {
          ElMessage.error('创建新配置时API Key是必填项')
          saving.value = false
          return
        }
        await api.post('/assistant/config/dify/', dataToSave)
        ElMessage.success('配置保存成功！')
      }
      
      // 清空API Key输入框（安全考虑）
      form.value.api_key = ''
      await loadConfig()
    } catch (error) {
      console.error('保存配置失败:', error)
      ElMessage.error(error.response?.data?.error || '保存配置失败')
    } finally {
      saving.value = false
    }
  })
}

const resetForm = () => {
  if (configForm.value) {
    configForm.value.resetFields()
  }
  if (currentConfig.value) {
    form.value = {
      api_url: currentConfig.value.api_url,
      api_key: '',
      is_active: currentConfig.value.is_active
    }
  }
}

onMounted(() => {
  loadConfig()
})
</script>

<style scoped lang="scss">
.dify-config-container {
  padding: 20px;
  max-width: 900px;
  margin: 0 auto;
}

.page-header {
  text-align: center;
  margin-bottom: 30px;

  h1 {
    font-size: 2rem;
    color: #2c3e50;
    margin-bottom: 10px;
  }

  p {
    color: #666;
    font-size: 1rem;
  }
}

.config-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.config-card, .info-card {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 600;
  }
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.switch-label {
  margin-left: 10px;
  color: #606266;
}

.el-form-item {
  margin-bottom: 24px;
}
</style>
