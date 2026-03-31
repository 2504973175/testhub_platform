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
                  <el-button size="small" @click="handleViewDocuments(kb)">
                    <el-icon><Document /></el-icon>
                    查看文档
                  </el-button>
                  <el-button size="small" type="primary" @click="handleUploadDocument(kb)">
                    <el-icon><Upload /></el-icon>
                    上传文档
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
        <el-form-item label="知识库名称" prop="name">
          <el-input v-model="newKnowledgeBase.name" placeholder="请输入知识库名称" />
        </el-form-item>
        <el-form-item label="知识库描述">
          <el-input v-model="newKnowledgeBase.description" type="textarea" placeholder="请输入知识库描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showAddKnowledgeBaseDialog = false">取消</el-button>
          <el-button type="primary" @click="handleCreateKnowledgeBase">确定</el-button>
        </span>
      </template>
    </el-dialog>
    
    <!-- 文档上传对话框 -->
    <el-dialog title="上传文档" v-model="showUploadDialog" width="500px">
      <el-form :model="uploadForm" label-width="100px">
        <el-form-item label="选择文件">
          <el-upload
            ref="upload"
            :auto-upload="false"
            :file-list="fileList"
            :on-change="handleFileChange"
            accept=".pdf,.docx,.txt,.md"
          >
            <el-button type="primary">选择文件</el-button>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showUploadDialog = false">取消</el-button>
          <el-button type="primary" @click="handleSubmitUpload">确定上传</el-button>
        </span>
      </template>
    </el-dialog>
    
    <!-- 文档列表对话框 -->
    <el-dialog title="文档列表" v-model="showDocumentsDialog" width="800px">
      <el-empty v-if="documents.length === 0" description="暂无文档" />
      <el-table v-else :data="documents" border stripe>
        <el-table-column prop="title" label="文档标题" />
        <el-table-column prop="file_type" label="文件类型" />
        <el-table-column label="文件大小">
          <template #default="scope">
            {{ formatFileSize(scope.row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column label="处理状态" width="120">
          <template #default="scope">
            <el-tag :type="getStatusTagType(scope.row.status)">
              {{ scope.row.status_display || scope.row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="embedding_count" label="切分块数" width="100" />
        <el-table-column prop="created_at" label="上传时间" />
        <el-table-column label="操作">
          <template #default="scope">
            <el-button size="small" @click="handleViewDocument(scope.row)">查看</el-button>
            <el-button size="small" type="danger" @click="handleDeleteDocument(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- 文档详情对话框 -->
    <el-dialog title="文档详情" v-model="showDocumentDetailDialog" width="600px">
      <div v-if="selectedDocument">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="文档标题">{{ selectedDocument.title }}</el-descriptions-item>
          <el-descriptions-item label="文件类型">{{ selectedDocument.file_type }}</el-descriptions-item>
          <el-descriptions-item label="处理状态">
            <el-tag :type="getStatusTagType(selectedDocument.status)">
              {{ selectedDocument.status_display || selectedDocument.status }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="切分块数">{{ selectedDocument.embedding_count || 0 }}</el-descriptions-item>
          <el-descriptions-item label="文件大小">{{ formatFileSize(selectedDocument.file_size || 0) }}</el-descriptions-item>
          <el-descriptions-item label="上传时间">{{ selectedDocument.created_at }}</el-descriptions-item>
        </el-descriptions>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button type="primary" @click="showDocumentDetailDialog = false">关闭</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Document, Upload, Delete } from '@element-plus/icons-vue'
import { getKnowledgeBases, createKnowledgeBase, updateKnowledgeBase, getDocumentsByKnowledgeBase, uploadDocument, deleteDocument, deleteKnowledgeBase } from '@/api/knowledge-base'

const knowledgeBases = ref([])
const showAddKnowledgeBaseDialog = ref(false)
const showUploadDialog = ref(false)
const showDocumentsDialog = ref(false)
const newKnowledgeBase = ref({ name: '', description: '' })
const uploadForm = ref({ file: null })
const fileList = ref([])
const currentKnowledgeBase = ref(null)
const documents = ref([])
const refreshTimer = ref(null)
const showDocumentDetailDialog = ref(false)
const selectedDocument = ref(null)

// 获取知识库列表
const fetchKnowledgeBases = async () => {
  try {
    const response = await getKnowledgeBases()
    // 确保正确解析后端返回的响应格式
    knowledgeBases.value = response.data.data || response.data
  } catch (error) {
    ElMessage.error('获取知识库列表失败')
  }
}

// 新建知识库
const handleCreateKnowledgeBase = async () => {
  try {
    await createKnowledgeBase(newKnowledgeBase.value)
    ElMessage.success('知识库创建成功')
    showAddKnowledgeBaseDialog.value = false
    newKnowledgeBase.value = { name: '', description: '' }
    fetchKnowledgeBases()
  } catch (error) {
    ElMessage.error('创建知识库失败')
  }
}

// 切换知识库状态
const handleToggleKnowledgeBase = async (kb) => {
  try {
    await updateKnowledgeBase(kb.id, { is_active: kb.is_active })
    ElMessage.success(`知识库已${kb.is_active ? '启用' : '禁用'}`)
  } catch (error) {
    kb.is_active = !kb.is_active
    ElMessage.error('更新知识库状态失败')
  }
}

// 上传文档
const handleUploadDocument = (kb) => {
  currentKnowledgeBase.value = kb
  showUploadDialog.value = true
}

// 处理文件选择
const handleFileChange = (file) => {
  uploadForm.value.file = file.raw
}

// 提交上传
const handleSubmitUpload = async () => {
  try {
    if (!currentKnowledgeBase.value || !currentKnowledgeBase.value.id) {
      ElMessage.error('请先选择一个知识库')
      return
    }
    await uploadDocument(currentKnowledgeBase.value.id, uploadForm.value.file)
    ElMessage.success('文档上传成功')
    showUploadDialog.value = false
    fileList.value = []
    // 上传成功后刷新文档列表
    handleViewDocuments(currentKnowledgeBase.value)
  } catch (error) {
    ElMessage.error('文档上传失败')
  }
}

// 查看文档
const handleViewDocuments = async (kb) => {
  currentKnowledgeBase.value = kb
  showDocumentsDialog.value = true
  try {
    console.log('开始获取文档列表，知识库ID:', kb.id)
    const response = await getDocumentsByKnowledgeBase(kb.id)
    console.log('获取文档列表响应:', response)
    console.log('响应数据:', response.data)
    // 确保正确解析后端返回的响应格式
    documents.value = response.data.data || response.data
    console.log('文档列表:', documents.value)
    scheduleAutoRefresh()
  } catch (error) {
    console.error('获取文档列表失败:', error)
    ElMessage.error('获取文档列表失败')
  }
}

const scheduleAutoRefresh = () => {
  if (refreshTimer.value) {
    clearTimeout(refreshTimer.value)
    refreshTimer.value = null
  }
  const hasPending = documents.value.some(d => ['uploaded', 'processing'].includes(d.status))
  if (showDocumentsDialog.value && currentKnowledgeBase.value && hasPending) {
    refreshTimer.value = setTimeout(() => {
      handleViewDocuments(currentKnowledgeBase.value)
    }, 3000)
  }
}

const getStatusTagType = (status) => {
  if (status === 'processed') return 'success'
  if (status === 'processing') return 'warning'
  if (status === 'failed') return 'danger'
  return 'info'
}

watch(showDocumentsDialog, (visible) => {
  if (!visible && refreshTimer.value) {
    clearTimeout(refreshTimer.value)
    refreshTimer.value = null
  }
})

// 格式化文件大小
const formatFileSize = (size) => {
  if (size < 1024) return size + 'B'
  if (size < 1024 * 1024) return (size / 1024).toFixed(2) + 'KB'
  return (size / (1024 * 1024)).toFixed(2) + 'MB'
}

// 查看文档详情
const handleViewDocument = (document) => {
  selectedDocument.value = document
  showDocumentDetailDialog.value = true
}

// 删除文档
const handleDeleteDocument = async (document) => {
  try {
    await deleteDocument(document.id)
    ElMessage.success('文档删除成功')
    handleViewDocuments(currentKnowledgeBase.value)
  } catch (error) {
    ElMessage.error('删除文档失败')
  }
}

// 删除知识库
const handleDeleteKnowledgeBase = async (kb) => {
  try {
    if (!confirm('确定要删除此知识库吗？删除后所有文档也将被删除。')) {
      return
    }
    await deleteKnowledgeBase(kb.id)
    ElMessage.success('知识库删除成功')
    fetchKnowledgeBases()
  } catch (error) {
    ElMessage.error('删除知识库失败')
  }
}

onMounted(() => {
  fetchKnowledgeBases()
})

onBeforeUnmount(() => {
  if (refreshTimer.value) {
    clearTimeout(refreshTimer.value)
    refreshTimer.value = null
  }
})
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
  height: 200px;
}

.kb-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.kb-description {
  margin-bottom: 20px;
  color: #666;
}

.kb-actions {
  display: flex;
  gap: 10px;
}

.kb-content {
  height: 120px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
</style>