# RAG知识库模块实现说明

## 功能概述

本项目新增了知识库模块，实现了RAG（Retrieval-Augmented Generation）技术结合用户提供的需求文档，输出更精准的测试用例。

## 主要功能

1. **知识库管理**：创建、编辑、删除知识库
2. **文档上传**：支持PDF、Word、TXT、Markdown等格式文档上传
3. **文档处理**：自动解析文档内容并生成向量嵌入
4. **RAG检索**：根据用户需求检索相关知识库内容
5. **增强测试用例生成**：结合RAG检索结果生成更精准的测试用例

## 技术架构

### 后端模块

1. **数据库模型**：`knowledge_base_models.py`
   - KnowledgeBase：知识库主表
   - KnowledgeDocument：知识库文档表
   - KnowledgeEmbedding：知识库向量表
   - RAGQueryRecord：RAG查询记录表

2. **服务层**：
   - `knowledge_base_services.py`：知识库文档处理服务
   - `rag_services.py`：RAG检索服务
   - `ai_models.py`：AI模型服务（已修改支持RAG增强）

3. **视图层**：
   - `knowledge_base_views.py`：知识库管理API
   - `views.py`：新增RAG相关API

### 前端模块

1. **知识库管理页面**：`knowledge-base.vue`
2. **API接口**：`knowledge-base.js`
3. **菜单集成**：已在左侧菜单添加知识库管理入口

## 使用流程

1. **创建知识库**：在知识库管理页面点击"新建知识库"
2. **上传文档**：选择知识库，点击"上传文档"，支持多种格式
3. **文档处理**：系统自动解析文档内容并生成向量嵌入
4. **生成测试用例**：在AI用例生成页面，选择知识库，系统会结合知识库内容生成更精准的测试用例

## 核心实现

### RAG检索流程

1. 用户输入需求描述
2. 系统将需求描述转换为向量
3. 在知识库中检索相似向量对应的文档片段
4. 将检索到的文档片段与原始需求结合，生成增强查询
5. 调用AI模型生成测试用例

### 关键代码

```python
# rag_services.py
async def augment_query_with_rag(query: str, knowledge_base_id: int, top_k: int = 5) -> str:
    # 检索相关文档
    relevant_chunks = await RAGService.retrieve_relevant_documents(query, knowledge_base_id, top_k)
    
    # 构建增强后的查询
    augmented_query = f"请根据以下知识库内容和用户需求生成测试用例：\n\n"
    augmented_query += "知识库内容：\n"
    for i, chunk in enumerate(relevant_chunks):
        augmented_query += f"【文档{i+1}】{chunk['document_title']}\n"
        augmented_query += f"{chunk['chunk_text']}\n\n"
    
    augmented_query += f"用户需求：{query}\n"
    
    return augmented_query
```

## 注意事项

1. 文档处理需要一定时间，上传后请等待处理完成
2. 向量嵌入服务需要配置相关API密钥
3. 建议文档大小不超过10MB，以保证处理效率
4. 目前支持的文档格式：PDF、Word、TXT、Markdown

## 未来优化方向

1. 支持更多文档格式（如Excel、PPT）
2. 优化向量检索算法，提高检索效率
3. 支持知识库权限管理
4. 增加文档版本控制
5. 优化前端界面，提升用户体验