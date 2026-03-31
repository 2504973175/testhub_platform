<template>
  <div class="knowledge-base-container">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>知识库管理</span>
          <el-button type="primary" @click="showAddKnowledgeBaseDialog = true">
            <el-icon><Plus /></el-icon>
            新建知识库
          </el-button>
        </div>
      </template>

      <div class="knowledge-base-list">
        <el-row :gutter="20">
          <el-col :span="8" v-for="kb in knowledgeBases" :key="kb.id">
            <el-card class="kb-card" shadow="hover">
              <template #header>
                <div class="kb-header">
                  <span>{{ kb.name }}</span>
                  <el-switch v-model="kb.is_active" @change="handleToggleKnowledgeBase(kb)" />
                </div>
              </template>
              <div class="kb-content">
                <p class="kb-description">{{ kb.description || '无描述' }}</p>
                <div class="kb-actions">
                  <el-button size="small" type="primary" @click="openKnowledgeBaseDrawer(kb)">
                    <el-icon><FolderOpened /></el-icon>
                    查看文档
                  </el-button>
                  <el-button size="small" type="danger" @click="handleDeleteKnowledgeBase(kb)">
                    <el-icon><Delete /></el-icon>
                    删除
                  </el-button>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>
    </el-card>

    <!-- 新建知识库对话框 -->
    <el-dialog title="新建知识库" v-model="showAddKnowledgeBaseDialog" width="500px">
      <el-form :model="newKnowledgeBase" label-width="100px">
        <el-form-item label="知识库名称">
          <el-input v-model="newKnowledgeBase.name" placeholder="请输入知识库名称" />
        </el-form-item>
        <el-form-item label="知识库描述">
          <el-input v-model="newKnowledgeBase.description" type="textarea" placeholder="请输入知识库描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddKnowledgeBaseDialog = false">取消</el-button>
        <el-button type="primary" @click="handleCreateKnowledgeBase">确定</el-button>
      </template>
    </el-dialog>

    <!-- 知识库文档抽屉 -->
    <el-drawer
      v-model="drawerVisible"
      :title="`${currentKb?.name || ''} — 文档管理`"
      size="80%"
      direction="rtl"
      destroy-on-close
    >
      <div class="drawer-body">
        <!-- 左侧文件夹面板 -->
        <div class="folder-panel">
          <div class="panel-header">
            <span>文件夹</span>
            <el-button size="small" type="primary" text @click="showAddFolderDialog = true">
              <el-icon><FolderAdd /></el-icon>
              新建
            </el-button>
          </div>

          <ul class="folder-list">
            <!-- 根目录 -->
            <li
              class="folder-item"
              :class="{ active: selectedFolder === '' }"
              @click="selectFolder('')"
            >
              <el-icon><Folder /></el-icon>
              <span>全部文档</span>
            </li>
            <!-- 各文件夹 -->
            <li
              v-for="folder in folders"
              :key="folder"
              class="folder-item"
              :class="{ active: selectedFolder === folder }"
              @click="selectFolder(folder)"
            >
              <el-icon><Folder /></el-icon>
              <span>{{ folder }}</span>
            </li>
          </ul>
        </div>

        <!-- 右侧文档面板 -->
        <div class="doc-panel">
          <div class="panel-header">
            <span>
              {{ selectedFolder === '' ? '全部文档' : selectedFolder }}
              <el-tag size="small" style="margin-left:8px">{{ documents.length }} 个</el-tag>
            </span>
            <el-button size="small" type="primary" @click="showUploadDialog = true">
              <el-icon><Upload /></el-icon>
              上传文档
            </el-button>
          </div>

          <el-empty v-if="documents.length === 0" description="暂无文档，请上传" />
          <el-table v-else :data="documents" border stripe>
            <el-table-column prop="title" label="文档标题" min-width="180" />
            <el-table-column prop="file_type" label="类型" width="80" />
            <el-table-column label="大小" width="100">
              <template #default="{ row }">{{ formatFileSize(row.file_size) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="110">
              <template #default="{ row }">
                <el-tag :type="getStatusTagType(row.status)">
                  {{ row.status_display || row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="embedding_count" label="切分块" width="80" />
            <el-table-column prop="created_at" label="上传时间" width="160" />
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-button size="small" type="danger" @click="handleDeleteDocument(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </el-drawer>

    <!-- 新建文件夹对话框 -->
    <el-dialog title="新建文件夹" v-model="showAddFolderDialog" width="400px">
      <el-input v-model="newFolderName" placeholder="请输入文件夹名称" @keyup.enter="handleCreateFolder" />
      <template #footer>
        <el-button @click="showAddFolderDialog = false">取消</el-button>
        <el-button type="primary" @click="handleCreateFolder">确定</el-button>
      </template>
    </el-dialog>

    <!-- 上传文档对话框 -->
    <el-dialog title="上传文档" v-model="showUploadDialog" width="480px">
      <el-form label-width="90px">
        <el-form-item label="目标文件夹">
          <el-select v-model="uploadFolder" placeholder="选择文件夹（可选）" clearable style="width:100%">
            <el-option label="根目录" value="" />
            <el-option v-for="f in folders" :key="f" :label="f" :value="f" />
          </el-select>
        </el-form-item>
        <el-form-item label="选择文件">
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :file-list="fileList"
            :on-change="handleFileChange"
            :limit="1"
            accept=".pdf,.docx,.txt,.md"
          >
            <el-button type="primary">选择文件</el-button>
            <template #tip>
              <div class="el-upload__tip">支持 PDF / Word / TXT / Markdown</div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showUploadDialog = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="handleSubmitUpload">确定上传</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Delete, Upload, Folder, FolderOpened, FolderAdd } from '@element-plus/icons-vue'
import {
  getKnowledgeBases, createKnowledgeBase, updateKnowledgeBase, deleteKnowledgeBase,
  deleteDocument,
  getFolders, createFolder, getDocumentsByFolder, uploadDocumentToFolder,
  getDocumentsByKnowledgeBase
} from '@/api/knowledge-base'

// ── 知识库列表 ──────────────────────────────────────────
const knowledgeBases = ref([])
const showAddKnowledgeBaseDialog = ref(false)
const newKnowledgeBase = ref({ name: '', description: '' })

const fetchKnowledgeBases = async () => {
  try {
    const res = await getKnowledgeBases()
    knowledgeBases.value = res.data.data || res.data
  } catch {
    ElMessage.error('获取知识库列表失败')
  }
}

const handleCreateKnowledgeBase = async () => {
  if (!newKnowledgeBase.value.name.trim()) {
    ElMessage.warning('请输入知识库名称')
    return
  }
  try {
    await createKnowledgeBase(newKnowledgeBase.value)
    ElMessage.success('知识库创建成功')
    showAddKnowledgeBaseDialog.value = false
    newKnowledgeBase.value = { name: '', description: '' }
    fetchKnowledgeBases()
  } catch {
    ElMessage.error('创建知识库失败')
  }
}

const handleToggleKnowledgeBase = async (kb) => {
  try {
    await updateKnowledgeBase(kb.id, { is_active: kb.is_active })
    ElMessage.success(`知识库已${kb.is_active ? '启用' : '禁用'}`)
  } catch {
    kb.is_active = !kb.is_active
    ElMessage.error('更新知识库状态失败')
  }
}

const handleDeleteKnowledgeBase = async (kb) => {
  if (!confirm(`确定要删除知识库「${kb.name}」吗？删除后所有文档也将被删除。`)) return
  try {
    await deleteKnowledgeBase(kb.id)
    ElMessage.success('知识库删除成功')
    fetchKnowledgeBases()
  } catch {
    ElMessage.error('删除知识库失败')
  }
}

// ── 抽屉 ────────────────────────────────────────────────
const drawerVisible = ref(false)
const currentKb = ref(null)

// ── 文件夹 ───────────────────────────────────────────────
const folders = ref([])
const selectedFolder = ref('')
const showAddFolderDialog = ref(false)
const newFolderName = ref('')

const fetchFolders = async () => {
  try {
    const res = await getFolders(currentKb.value.id)
    folders.value = res.data.data || []
  } catch {
    folders.value = []
  }
}

const handleCreateFolder = async () => {
  const name = newFolderName.value.trim()
  if (!name) { ElMessage.warning('请输入文件夹名称'); return }
  if (folders.value.includes(name)) { ElMessage.warning('文件夹已存在'); return }
  try {
    await createFolder(currentKb.value.id, name)
    folders.value.push(name)
    newFolderName.value = ''
    showAddFolderDialog.value = false
    ElMessage.success('文件夹创建成功')
  } catch {
    ElMessage.error('创建文件夹失败')
  }
}

const selectFolder = (folder) => {
  selectedFolder.value = folder
  fetchDocuments()
}

// ── 文档列表 ─────────────────────────────────────────────
const documents = ref([])
const refreshTimer = ref(null)

const fetchDocuments = async () => {
  if (!currentKb.value) return
  try {
    let res
    if (selectedFolder.value === '__all__') {
      res = await getDocumentsByKnowledgeBase(currentKb.value.id)
      documents.value = res.data.data || res.data
    } else {
      res = await getDocumentsByFolder(currentKb.value.id, selectedFolder.value)
      documents.value = res.data.data || []
    }
    scheduleAutoRefresh()
  } catch {
    ElMessage.error('获取文档列表失败')
  }
}

const scheduleAutoRefresh = () => {
  if (refreshTimer.value) clearTimeout(refreshTimer.value)
  const hasPending = documents.value.some(d => ['uploaded', 'processing'].includes(d.status))
  if (drawerVisible.value && hasPending) {
    refreshTimer.value = setTimeout(fetchDocuments, 3000)
  }
}

watch(drawerVisible, (v) => {
  if (!v && refreshTimer.value) {
    clearTimeout(refreshTimer.value)
    refreshTimer.value = null
  }
})

const openKnowledgeBaseDrawer = async (kb) => {
  currentKb.value = kb
  selectedFolder.value = ''
  drawerVisible.value = true
  await fetchFolders()
  await fetchDocuments()
}

const handleDeleteDocument = async (doc) => {
  if (!confirm(`确定要删除文档「${doc.title}」吗？`)) return
  try {
    await deleteDocument(doc.id)
    ElMessage.success('文档删除成功')
    fetchDocuments()
    fetchFolders()
  } catch {
    ElMessage.error('删除文档失败')
  }
}

// ── 上传 ─────────────────────────────────────────────────
const showUploadDialog = ref(false)
const uploadFolder = ref('')
const fileList = ref([])
const uploading = ref(false)
const selectedFile = ref(null)

// 打开上传时，默认选中当前文件夹
watch(showUploadDialog, (v) => {
  if (v) uploadFolder.value = selectedFolder.value
})

const handleFileChange = (file) => {
  selectedFile.value = file.raw
}

const handleSubmitUpload = async () => {
  if (!selectedFile.value) { ElMessage.warning('请选择文件'); return }
  uploading.value = true
  try {
    await uploadDocumentToFolder(currentKb.value.id, selectedFile.value, uploadFolder.value)
    ElMessage.success('文档上传成功')
    showUploadDialog.value = false
    fileList.value = []
    selectedFile.value = null
    await fetchFolders()
    // 切换到上传的文件夹
    selectedFolder.value = uploadFolder.value
    await fetchDocuments()
  } catch {
    ElMessage.error('文档上传失败')
  } finally {
    uploading.value = false
  }
}

// ── 工具函数 ─────────────────────────────────────────────
const formatFileSize = (size) => {
  if (!size) return '-'
  if (size < 1024) return size + 'B'
  if (size < 1024 * 1024) return (size / 1024).toFixed(1) + 'KB'
  return (size / (1024 * 1024)).toFixed(1) + 'MB'
}

const getStatusTagType = (status) => {
  if (status === 'processed') return 'success'
  if (status === 'processing') return 'warning'
  if (status === 'failed') return 'danger'
  return 'info'
}

onMounted(fetchKnowledgeBases)
</script>

<style scoped>
.knowledge-base-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.knowledge-base-list {
  margin-top: 20px;
}

.kb-card {
  margin-bottom: 20px;
}

.kb-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.kb-description {
  margin-bottom: 16px;
  color: #666;
  min-height: 40px;
}

.kb-actions {
  display: flex;
  gap: 8px;
}

.kb-content {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

/* 抽屉内布局 */
.drawer-body {
  display: flex;
  height: 100%;
  gap: 0;
}

.folder-panel {
  width: 200px;
  flex-shrink: 0;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  padding: 0 0 16px 0;
}

.doc-panel {
  flex: 1;
  padding: 0 20px 16px 20px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #e4e7ed;
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 12px;
}

.folder-list {
  list-style: none;
  margin: 0;
  padding: 8px 0;
  flex: 1;
  overflow-y: auto;
}

.folder-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  cursor: pointer;
  font-size: 14px;
  color: #303133;
  transition: background 0.2s;
  border-radius: 0;
}

.folder-item:hover {
  background: #f5f7fa;
}

.folder-item.active {
  background: #ecf5ff;
  color: #409eff;
  font-weight: 600;
}
</style>
