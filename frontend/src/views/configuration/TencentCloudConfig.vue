<template>
  <div class="tencent-config">
    <div class="page-header">
      <h2>☁️ 腾讯云配置</h2>
      <p class="desc">配置腾讯云 SecretId/SecretKey 及智能体 AppKey，用于 AI 用例生成和文档解析。</p>
    </div>

    <div class="config-card">
      <div class="form-group">
        <label>SecretId <span class="required">*</span></label>
        <input v-model="form.secret_id" type="text" class="form-input" placeholder="腾讯云 API SecretId" />
      </div>

      <div class="form-group">
        <label>SecretKey <span class="required">*</span></label>
        <input v-model="form.secret_key" type="password" class="form-input"
          :placeholder="hasSecretKey ? '已配置，留空不修改' : '腾讯云 API SecretKey'" />
        <small v-if="hasSecretKey" class="hint">已配置，如需修改请输入新值</small>
      </div>

      <div class="form-group">
        <label>LKE AppKey <span class="required">*</span></label>
        <input v-model="form.lke_app_key" type="password" class="form-input"
          :placeholder="hasLkeAppKey ? '已配置，留空不修改' : '智能体 AppKey（用于 AI 用例生成）'" />
        <small v-if="hasLkeAppKey" class="hint">已配置，如需修改请输入新值</small>
      </div>

      <div class="form-group">
        <label>地域</label>
        <select v-model="form.lke_region" class="form-input">
          <option value="ap-guangzhou">华南-广州（ap-guangzhou）</option>
          <option value="ap-beijing">华北-北京（ap-beijing）</option>
          <option value="ap-shanghai">华东-上海（ap-shanghai）</option>
          <option value="ap-chengdu">西南-成都（ap-chengdu）</option>
        </select>
      </div>

      <div v-if="updatedAt" class="updated-at">上次更新：{{ updatedAt }}</div>

      <div class="form-actions">
        <button class="save-btn" :disabled="saving" @click="save">
          {{ saving ? '保存中...' : '💾 保存配置' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/utils/api'

const form = ref({ secret_id: '', secret_key: '', lke_app_key: '', lke_region: 'ap-guangzhou' })
const hasSecretKey = ref(false)
const hasLkeAppKey = ref(false)
const updatedAt = ref('')
const saving = ref(false)

onMounted(async () => {
  const res = await api.get('/requirement-analysis/tencent-cloud-config/')
  const d = res.data.data
  form.value.secret_id = d.secret_id || ''
  form.value.lke_region = d.lke_region || 'ap-guangzhou'
  hasSecretKey.value = d.has_secret_key
  hasLkeAppKey.value = d.has_lke_app_key
  updatedAt.value = d.updated_at || ''
})

const save = async () => {
  saving.value = true
  try {
    await api.post('/requirement-analysis/tencent-cloud-config/', form.value)
    ElMessage.success('配置保存成功')
    // 刷新状态
    const res = await api.get('/requirement-analysis/tencent-cloud-config/')
    const d = res.data.data
    hasSecretKey.value = d.has_secret_key
    hasLkeAppKey.value = d.has_lke_app_key
    updatedAt.value = d.updated_at || ''
    form.value.secret_key = ''
    form.value.lke_app_key = ''
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.tencent-config { padding: 20px; max-width: 600px; }
.page-header { margin-bottom: 24px; }
.page-header h2 { margin: 0 0 6px; }
.desc { color: #888; font-size: 13px; margin: 0; }
.config-card {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0,0,0,.06);
}
.form-group { margin-bottom: 20px; }
.form-group label { display: block; font-size: 13px; font-weight: 500; margin-bottom: 6px; color: #333; }
.required { color: #f56c6c; }
.form-input {
  width: 100%;
  padding: 9px 12px;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  font-size: 14px;
  box-sizing: border-box;
  outline: none;
  transition: border-color .2s;
}
.form-input:focus { border-color: #409eff; }
.hint { font-size: 12px; color: #aaa; margin-top: 4px; display: block; }
.updated-at { font-size: 12px; color: #bbb; margin-bottom: 16px; }
.form-actions { text-align: right; }
.save-btn {
  padding: 9px 24px;
  background: #409eff;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
}
.save-btn:hover:not(:disabled) { background: #337ecc; }
.save-btn:disabled { background: #a0cfff; cursor: not-allowed; }
</style>
