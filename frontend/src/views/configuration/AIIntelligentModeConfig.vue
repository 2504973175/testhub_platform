<template>
  <div class="ai-mode-config">
    <div class="page-header">
      <h1>🧠 AI智能模式配置</h1>
      <p>配置Browser-use执行时的智能模式与模型参数</p>
    </div>

    <div class="main-content">
      <div class="model-config-card">
        <div class="card-header">
          <h2>模型参数配置</h2>
          <el-tooltip content="配置文本模式使用的模型参数。" placement="top">
            <el-icon><InfoFilled /></el-icon>
          </el-tooltip>
        </div>
        
        <el-tabs v-model="activeTab" type="border-card">
          <el-tab-pane label="文本模式模型" name="text">
            <div class="tab-desc">
              <span class="icon">📝</span> 文本模式：基于DOM树解析，快速高效，适合结构化页面。
            </div>
            <model-form 
              v-model="config.text_model" 
              type="text"
              @test="testConnection"
            />
          </el-tab-pane>

        </el-tabs>

        <div class="actions">
          <el-button type="primary" size="large" @click="saveConfig" :loading="saving">保存所有配置</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, defineComponent, h } from 'vue'
import { InfoFilled } from '@element-plus/icons-vue'
import { ElMessage, ElForm, ElFormItem, ElSelect, ElOption, ElInput, ElButton } from 'element-plus'
import api from '@/utils/api'

// 内联组件：模型表单
const ModelForm = defineComponent({
  props: ['modelValue', 'type'],
  emits: ['update:modelValue', 'test'],
  setup(props, { emit }) {
    const testing = ref(false)
    
    const handleTest = async () => {
      testing.value = true
      try {
        await emit('test', props.modelValue)
      } finally {
        testing.value = false
      }
    }

    return () => h(ElForm, { model: props.modelValue, labelWidth: '120px' }, () => [
      h(ElFormItem, { label: '模型提供商' }, () => 
        h(ElSelect, { 
          modelValue: props.modelValue.provider,
          'onUpdate:modelValue': (val) => emit('update:modelValue', { ...props.modelValue, provider: val }),
          placeholder: '选择提供商',
          style: { width: '100%' }
        }, () => [
          h(ElOption, { label: 'OpenAI', value: 'openai' }),
          h(ElOption, { label: 'Azure OpenAI', value: 'azure_openai' }),
          h(ElOption, { label: 'Anthropic', value: 'anthropic' }),
          h(ElOption, { label: 'Google Gemini', value: 'google_gemini' }),
          h(ElOption, { label: 'DeepSeek', value: 'deepseek' }),
          h(ElOption, { label: '硅基流动 (SiliconFlow)', value: 'siliconflow' }),
          h(ElOption, { label: '其他 (Other)', value: 'other' })
        ])
      ),
      h(ElFormItem, { label: '模型名称' }, () => 
        h(ElInput, {
          modelValue: props.modelValue.model_name,
          'onUpdate:modelValue': (val) => emit('update:modelValue', { ...props.modelValue, model_name: val }),
          placeholder: '例如: gpt-4o, claude-3-5-sonnet'
        })
      ),
      h(ElFormItem, { label: 'API Key' }, () => 
        h(ElInput, {
          modelValue: props.modelValue.api_key,
          'onUpdate:modelValue': (val) => emit('update:modelValue', { ...props.modelValue, api_key: val }),
          type: 'password',
          placeholder: '输入API Key'
        })
      ),
      h(ElFormItem, { label: 'Base URL' }, () => 
        h(ElInput, {
          modelValue: props.modelValue.base_url,
          'onUpdate:modelValue': (val) => emit('update:modelValue', { ...props.modelValue, base_url: val }),
          placeholder: '可选，例如: https://api.openai.com/v1'
        })
      ),
      h(ElFormItem, {}, () => 
        h(ElButton, { 
          type: 'success', 
          plain: true, 
          loading: testing.value,
          onClick: handleTest 
        }, () => '测试连接')
      )
    ])
  }
})

const saving = ref(false)
const activeTab = ref('text')
const config = ref({
  text_model: {
    provider: 'openai',
    model_name: 'gpt-4o',
    api_key: '',
    base_url: ''
  }
})

const loadConfig = async () => {
  try {
    const response = await api.get('/ui-automation/config/ai-mode/')
    if (response.data) {
      config.value = {
        ...config.value,
        ...response.data,
        text_model: { ...config.value.text_model, ...(response.data.text_model || {}) }
      }
    }
  } catch (error) {
    console.error('加载配置失败:', error)
    ElMessage.error('加载配置失败')
  }
}

const testConnection = async (modelConfig) => {
  if (!modelConfig.api_key) {
    ElMessage.warning('请先输入API Key')
    return
  }
  
  try {
    await api.post('/ui-automation/config/ai-mode/test_connection/', modelConfig)
    ElMessage.success('连接测试成功！')
  } catch (error) {
    console.error('连接测试失败:', error)
    const msg = error.response?.data?.error || '连接测试失败'
    ElMessage.error(msg)
    throw error
  }
}

const saveConfig = async () => {
  saving.value = true
  try {
    await api.post('/ui-automation/config/ai-mode/', config.value)
    ElMessage.success('配置保存成功')
  } catch (error) {
    console.error('保存配置失败:', error)
    ElMessage.error('保存配置失败')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadConfig()
})
</script>

<style scoped>
.ai-mode-config {
  padding: 20px;
  max-width: 1000px;
  margin: 0 auto;
}

.page-header {
  text-align: center;
  margin-bottom: 40px;
}

.page-header h1 {
  font-size: 2.5rem;
  color: #2c3e50;
  margin-bottom: 10px;
}

.page-header p {
  color: #666;
  font-size: 1.1rem;
}

.main-content {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.model-config-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
}

.card-header h2 {
  margin: 0;
  font-size: 1.2rem;
  color: #303133;
}

.tab-desc {
  margin-bottom: 20px;
  padding: 10px 15px;
  background-color: #f4f4f5;
  border-radius: 4px;
  color: #606266;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.tab-desc .icon {
  font-size: 18px;
}

.actions {
  margin-top: 30px;
  display: flex;
  justify-content: center;
}
</style>
