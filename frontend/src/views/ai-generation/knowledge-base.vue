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
                  <el-switch v-model="kb.is_active" @change="toggleKnowledgeBase(kb)" />
                </div>
              </template>
              <div class="kb-content">
                <p class="kb-description">{{ kb.description || '无描述' }}</p>
                <div class="kb-actions">
                  <el-button size="small" @click="viewDocuments(kb)">
                    <el-icon><Document /></el-icon>
                    查看文档
                  </el-button>
                  <el-button size="small" type="primary" @click="uploadDocument(kb)">
                    <el-icon><Upload /></el-icon>
                    上传文档
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
          <el-button type="primary" @click="createKnowledgeBase">确定</el-button>
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
          <el-button type="primary" @click="submitUpload">确定上传</el-button>
        </span>
      </template>
    </el-dialog>
    
    <!-- 文档列表对话框 -->
    <el-dialog title="文档列表" v-model="showDocumentsDialog" width="800px">
      <el-table :data="documents" border stripe>
        <el-table-column prop="title" label="文档标题" />
        <el-table-column prop="file_type" label="文件类型" />
        <el-table-column prop="file_size" label="文件大小" formatter="formatFileSize" />
        <el-table-column prop="status" label="处理状态" />
        <el-table-column prop="created_at" label="上传时间" />
        <el-table-column label="操作">
          <template #default="scope">
            <el-button size="small" @click="viewDocument(scope.row)">查看</el-button>
            <el-button size="small" type="danger" @click="deleteDocument(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Document, Upload } from '@element-plus/icons-vue'

const knowledgeBases = ref([])
const showAddKnowledgeBaseDialog = ref(false)
const showUploadDialog = ref(false)
const showDocumentsDialog = ref(false)
const newKnowledgeBase = ref({ name: '', description: '' })
const uploadForm = ref({ file: null })
const fileList = ref([])
const currentKnowledgeBase = ref(null)
const documents = ref([])

// 获取知识库列表
const getKnowledgeBases = async () => {
  try {
    // 这里需要替换为实际的API调用
    // const response = await getKnowledgeBasesAPI()
    // knowledgeBases.value = response.data
    knowledgeBases.value = [
      { id: 1, name: '产品需求知识库', description: '存储产品需求文档', is_active: true },
      { id: 2, name: '测试用例知识库', description: '存储测试用例模板和规范', is_active: false },
    ]
  } catch (error) {
    ElMessage.error('获取知识库列表失败')
  }
}

// 新建知识库
const createKnowledgeBase = async () => {
  try {
    // 这里需要替换为实际的API调用
    // await createKnowledgeBaseAPI(newKnowledgeBase.value)
    ElMessage.success('知识库创建成功')
    showAddKnowledgeBaseDialog.value = false
    newKnowledgeBase.value = { name: '', description: '' }
    getKnowledgeBases()
  } catch (error) {
    ElMessage.error('创建知识库失败')
  }
}

// 切换知识库状态
const toggleKnowledgeBase = async (kb) => {
  try {
    // 这里需要替换为实际的API调用
    // await updateKnowledgeBaseAPI(kb.id, { is_active: kb.is_active })
    ElMessage.success(`知识库已${kb.is_active ? '启用' : '禁用'}`)
  } catch (error) {
    kb.is_active = !kb.is_active
    ElMessage.error('更新知识库状态失败')
  }
}

// 上传文档
const uploadDocument = (kb) => {
  currentKnowledgeBase.value = kb
  showUploadDialog.value = true
}

// 处理文件选择
const handleFileChange = (file) => {
  uploadForm.value.file = file.raw
}

// 提交上传
const submitUpload = async () => {
  try {
    // 这里需要替换为实际的API调用
    // await uploadDocumentAPI(currentKnowledgeBase.value.id, uploadForm.value.file)
    ElMessage.success('文档上传成功')
    showUploadDialog.value = false
    fileList.value = []
  } catch (error) {
    ElMessage.error('文档上传失败')
  }
}

// 查看文档
const viewDocuments = async (kb) => {
  currentKnowledgeBase.value = kb
  showDocumentsDialog.value = true
  try {
    // 这里需要替换为实际的API调用
    // const response = await getDocumentsAPI(kb.id)
    // documents.value = response.data
    documents.value = [
      { id: 1, title: '产品需求文档.pdf', file_type: 'pdf', file_size: 1024 * 1024, status: '已处理', created_at: '2024-01-01' },
      { id: 2, title: '测试用例规范.docx', file_type: 'docx', file_size: 512 * 1024, status: '处理中', created_at: '2024-01-02' },
    ]
  } catch (error) {
    ElMessage.error('获取文档列表失败')
  }
}

// 格式化文件大小
const formatFileSize = (size) => {
  if (size < 1024) return size + 'B'
  if (size < 1024 * 1024) return (size / 1024).toFixed(2) + 'KB'
  return (size / (1024 * 1024)).toFixed(2) + 'MB'
}

// 查看文档详情
const viewDocument = (document) => {
  // 这里可以添加查看文档详情的逻辑
  console.log('查看文档:', document)
}

// 删除文档
const deleteDocument = async (document) => {
  try {
    // 这里需要替换为实际的API调用
    // await deleteDocumentAPI(document.id)
    ElMessage.success('文档删除成功')
    viewDocuments(currentKnowledgeBase.value)
  } catch (error) {
    ElMessage.error('删除文档失败')
  }
}

onMounted(() => {
  getKnowledgeBases()
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