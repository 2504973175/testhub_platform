/**
 * 知识库模块API
 */

import request from '@/utils/request'

// 获取知识库列表
export function getKnowledgeBases() {
  return request({
    url: '/requirement-analysis/knowledge-bases/',
    method: 'get'
  })
}

// 创建知识库
export function createKnowledgeBase(data) {
  return request({
    url: '/requirement-analysis/knowledge-bases/create/',
    method: 'post',
    data
  })
}

// 更新知识库
export function updateKnowledgeBase(kbId, data) {
  return request({
    url: `/requirement-analysis/knowledge-bases/${kbId}/update/`,
    method: 'post',
    data
  })
}

// 获取知识库下的文档列表
export function getDocumentsByKnowledgeBase(kbId) {
  return request({
    url: `/requirement-analysis/knowledge-bases/${kbId}/documents/`,
    method: 'get'
  })
}

// 上传文档
export function uploadDocument(kbId, file) {
  const formData = new FormData()
  formData.append('file', file)
  
  return request({
    url: `/requirement-analysis/knowledge-bases/${kbId}/documents/upload/`,
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 删除文档
export function deleteDocument(docId) {
  return request({
    url: `/requirement-analysis/knowledge-bases/documents/${docId}/delete/`,
    method: 'post'
  })
}

// RAG检索
export function ragRetrieve(query, kbId) {
  return request({
    url: '/requirement-analysis/rag/retrieve/',
    method: 'post',
    data: {
      query,
      knowledge_base_id: kbId
    }
  })
}

// 使用RAG生成测试用例
export function ragGenerateTestCases(taskId, kbId) {
  return request({
    url: '/requirement-analysis/rag/generate-test-cases/',
    method: 'post',
    data: {
      task_id: taskId,
      knowledge_base_id: kbId
    }
  })
}