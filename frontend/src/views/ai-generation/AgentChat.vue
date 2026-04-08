<template>
  <div class="agent-chat">
    <div class="chat-header">
      <el-button text @click="$router.push('/ai-generation/agent-config')">← 返回</el-button>
      <span class="agent-name">🤖 {{ agentName }}</span>
      <el-button size="small" @click="clearChat">清空对话</el-button>
    </div>

    <div class="chat-messages" ref="messagesRef">
      <div v-if="messages.length === 0" class="empty-tip">发送消息开始对话</div>
      <div v-for="(msg, i) in messages" :key="i" :class="['message', msg.role]">
        <div class="bubble">
          <div class="content" v-html="renderContent(msg.content)"></div>
          <div v-if="msg.token_usage" class="token-info">
            Token: {{ msg.token_usage.total_tokens }}
          </div>
        </div>
      </div>
      <div v-if="loading" class="message assistant">
        <div class="bubble"><span class="typing">智能体思考中...</span></div>
      </div>
    </div>

    <div class="chat-input">
      <el-input
        v-model="inputText"
        type="textarea"
        :rows="3"
        placeholder="输入消息，Ctrl+Enter 发送"
        @keydown.ctrl.enter="send"
        resize="none"
      />
      <el-button type="primary" :loading="loading" @click="send" class="send-btn">发送</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '@/utils/api'

const route = useRoute()
const router = useRouter()
const agentId = route.params.id
const agentName = ref('智能体')
const messages = ref([])
const inputText = ref('')
const loading = ref(false)
const messagesRef = ref(null)
const sessionId = ref('')

const scrollToBottom = async () => {
  await nextTick()
  if (messagesRef.value) messagesRef.value.scrollTop = messagesRef.value.scrollHeight
}

const renderContent = (text) => {
  // 简单处理换行
  return text.replace(/\n/g, '<br>')
}

const clearChat = () => {
  messages.value = []
  sessionId.value = ''
}

const send = async () => {
  const content = inputText.value.trim()
  if (!content || loading.value) return

  messages.value.push({ role: 'user', content })
  inputText.value = ''
  loading.value = true
  scrollToBottom()

  try {
    const res = await api.post(`/requirement-analysis/agents/${agentId}/chat/`, {
      content,
      session_id: sessionId.value || undefined,
    }, { timeout: 120000 })
    const data = res.data.data
    sessionId.value = data.session_id
    messages.value.push({
      role: 'assistant',
      content: data.reply,
      token_usage: data.token_usage,
    })
  } catch (e) {
    ElMessage.error('发送失败: ' + (e.response?.data?.message || e.message))
    messages.value.push({ role: 'assistant', content: '⚠️ 请求失败，请重试' })
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

onMounted(async () => {
  try {
    const res = await api.get(`/requirement-analysis/agents/${agentId}/`)
    agentName.value = res.data.data?.name || '智能体'
  } catch {}
})
</script>

<style scoped>
.agent-chat {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 120px);
  padding: 16px;
}
.chat-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}
.agent-name { font-size: 16px; font-weight: 600; flex: 1; }
.chat-messages {
  flex: 1;
  overflow-y: auto;
  border: 1px solid #eee;
  border-radius: 8px;
  padding: 16px;
  background: #fafafa;
  margin-bottom: 12px;
}
.empty-tip { text-align: center; color: #aaa; margin-top: 40px; }
.message { display: flex; margin-bottom: 16px; }
.message.user { justify-content: flex-end; }
.message.assistant { justify-content: flex-start; }
.bubble {
  max-width: 70%;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
}
.message.user .bubble { background: #409eff; color: #fff; border-radius: 12px 2px 12px 12px; }
.message.assistant .bubble { background: #fff; border: 1px solid #e0e0e0; border-radius: 2px 12px 12px 12px; }
.token-info { font-size: 11px; color: #aaa; margin-top: 4px; }
.typing { color: #999; font-style: italic; }
.chat-input { display: flex; gap: 8px; align-items: flex-end; }
.chat-input .el-textarea { flex: 1; }
.send-btn { height: 72px; }
</style>
