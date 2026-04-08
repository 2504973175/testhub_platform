<template>
  <div class="agent-config">
    <div class="page-header">
      <h2>🤖 智能体配置</h2>
      <el-button type="primary" @click="openDialog()">+ 添加智能体</el-button>
    </div>

    <el-table :data="agents" border stripe>
      <el-table-column prop="name" label="名称" min-width="140" />
      <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
      <el-table-column label="AppKey" width="120">
        <template #default="{ row }">
          <span>{{ row.has_key ? '已配置' : '未配置' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
            {{ row.is_active ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="160" />
      <el-table-column label="操作" width="180">
        <template #default="{ row }">
          <el-button size="small" @click="$router.push(`/ai-generation/agent-chat/${row.id}`)">对话</el-button>
          <el-button size="small" type="primary" @click="openDialog(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="deleteAgent(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑智能体' : '添加智能体'" width="500px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="智能体名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" rows="2" />
        </el-form-item>
        <el-form-item label="BotAppKey" required>
          <el-input v-model="form.bot_app_key" type="password" show-password
            :placeholder="form.id ? '不修改请留空' : '输入 BotAppKey'" />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import api from '@/utils/api'

const router = useRouter()
const agents = ref([])
const dialogVisible = ref(false)
const saving = ref(false)
const form = ref({ id: null, name: '', description: '', bot_app_key: '', is_active: true })

const load = async () => {
  const res = await api.get('/requirement-analysis/agents/')
  agents.value = res.data.data || []
}

const openDialog = (row = null) => {
  form.value = row
    ? { id: row.id, name: row.name, description: row.description, bot_app_key: '', is_active: row.is_active }
    : { id: null, name: '', description: '', bot_app_key: '', is_active: true }
  dialogVisible.value = true
}

const save = async () => {
  if (!form.value.name) { ElMessage.warning('请填写名称'); return }
  if (!form.value.id && !form.value.bot_app_key) { ElMessage.warning('请填写 BotAppKey'); return }
  saving.value = true
  try {
    if (form.value.id) {
      await api.patch(`/requirement-analysis/agents/${form.value.id}/`, form.value)
    } else {
      await api.post('/requirement-analysis/agents/create/', form.value)
    }
    ElMessage.success('保存成功')
    dialogVisible.value = false
    load()
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

const deleteAgent = async (row) => {
  await ElMessageBox.confirm(`确定删除「${row.name}」？`, '提示', { type: 'warning' })
  await api.delete(`/requirement-analysis/agents/${row.id}/`)
  ElMessage.success('已删除')
  load()
}

onMounted(load)
</script>

<style scoped>
.agent-config { padding: 20px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h2 { margin: 0; }
</style>
