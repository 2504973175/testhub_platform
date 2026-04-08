<template>
  <div class="agent-dialog">
    <!-- 消息区 -->
    <div class="messages-area" ref="messagesRef">
      <div v-if="messages.length === 0" class="welcome">
        <h2>{{ currentAgent ? currentAgent.name : '请先选择智能体' }}</h2>
        <p>{{ currentAgent ? currentAgent.description || '开始对话吧' : '在左下角选择一个智能体' }}</p>
      </div>
      <div v-for="(msg, i) in messages" :key="i" :class="['msg', msg.role]">
        <div class="avatar">{{ msg.role === 'user' ? '我' : '🤖' }}</div>
        <div class="bubble">
          <div class="content" v-html="renderMd(msg.content)"></div>
          <div v-if="msg.token_usage?.total_tokens" class="meta">
            Token: {{ msg.token_usage.total_tokens }}
          </div>
        </div>
      </div>
      <div v-if="loading" class="msg assistant">
        <div class="avatar">🤖</div>
        <div class="bubble"><span class="dots">···</span></div>
      </div>
    </div>

    <!-- 输入区 -->
    <div class="input-area">
      <div class="input-box">
        <textarea
          v-model="inputText"
          :placeholder="currentAgent ? `向「${currentAgent.name}」发送消息` : '请先在左下角选择智能体'"
          @keydown.ctrl.enter.prevent="send"
          @keydown.meta.enter.prevent="send"
          rows="3"
        />
        <div class="toolbar">
          <!-- 智能体选择器 -->
          <div class="agent-selector" ref="selectorRef">
            <button class="agent-btn" @click="toggleSelector">
              <span class="agent-icon">🤖</span>
              <span class="agent-label">{{ currentAgent ? currentAgent.name : '选择智能体' }}</span>
              <span class="arrow">▾</span>
            </button>
            <div v-if="showSelector" class="agent-dropdown">
              <div
                v-for="a in agents"
                :key="a.id"
                :class="['agent-option', { active: currentAgent?.id === a.id }]"
                @click="selectAgent(a)"
              >
                <span class="dot" :class="{ on: a.is_active }"></span>
                {{ a.name }}
              </div>
              <div v-if="agents.length === 0" class="no-agent">
                暂无智能体，请先
                <router-link to="/ai-generation/agent-config">添加配置</router-link>
              </div>
            </div>
          </div>

          <button class="clear-btn" @click="clearChat" title="清空对话">↺</button>
          <button class="send-btn" :disabled="!currentAgent || loading" @click="send">
            {{ loading ? '···' : '发送' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/utils/api'

const agents = ref([])
const currentAgent = ref(null)
const messages = ref([])
const inputText = ref('')
const loading = ref(false)
const messagesRef = ref(null)
const selectorRef = ref(null)
const showSelector = ref(false)
const sessionId = ref('')

const renderMd = (text) => text.replace(/\n/g, '<br>')

const scrollToBottom = async () => {
  await nextTick()
  if (messagesRef.value) messagesRef.value.scrollTop = messagesRef.value.scrollHeight
}

const toggleSelector = () => { showSelector.value = !showSelector.value }

const selectAgent = (a) => {
  if (currentAgent.value?.id !== a.id) {
    currentAgent.value = a
    messages.value = []
    sessionId.value = ''
  }
  showSelector.value = false
}

const clearChat = () => {
  messages.value = []
  sessionId.value = ''
}

const send = async () => {
  const content = inputText.value.trim()
  if (!content || !currentAgent.value || loading.value) return

  messages.value.push({ role: 'user', content })
  inputText.value = ''
  loading.value = true
  scrollToBottom()

  try {
    const res = await api.post(
      `/requirement-analysis/agents/${currentAgent.value.id}/chat/`,
      { content, session_id: sessionId.value || undefined },
      { timeout: 120000 }
    )
    const data = res.data.data
    sessionId.value = data.session_id
    messages.value.push({ role: 'assistant', content: data.reply, token_usage: data.token_usage })
  } catch (e) {
    ElMessage.error('发送失败: ' + (e.response?.data?.message || e.message))
    messages.value.push({ role: 'assistant', content: '⚠️ 请求失败，请重试' })
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

// 点击外部关闭下拉
const onClickOutside = (e) => {
  if (selectorRef.value && !selectorRef.value.contains(e.target)) showSelector.value = false
}

onMounted(async () => {
  document.addEventListener('click', onClickOutside)
  const res = await api.get('/requirement-analysis/agents/')
  agents.value = (res.data.data || []).filter(a => a.is_active)
  if (agents.value.length > 0) currentAgent.value = agents.value[0]
})

onBeforeUnmount(() => document.removeEventListener('click', onClickOutside))
</script>

<style scoped>
.agent-dialog {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 120px);
  background: #f4f6fb;
}

/* 消息区 */
.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 40px 20%;
}

.welcome {
  text-align: center;
  margin-top: 80px;
  color: #555;
}
.welcome h2 { font-size: 22px; font-weight: 700; margin-bottom: 8px; }
.welcome p { color: #999; }

.msg {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}
.msg.user { flex-direction: row-reverse; }

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #e8eaf6;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}
.msg.user .avatar { background: #409eff; color: #fff; }

.bubble {
  max-width: 65%;
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.7;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0,0,0,.06);
}
.msg.user .bubble { background: #409eff; color: #fff; }

.meta { font-size: 11px; color: #bbb; margin-top: 6px; }
.dots { font-size: 20px; letter-spacing: 4px; color: #aaa; }

/* 输入区 */
.input-area {
  padding: 16px 20%;
  background: #f4f6fb;
}

.input-box {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,.08);
  padding: 14px 16px 10px;
}

.input-box textarea {
  width: 100%;
  border: none;
  outline: none;
  resize: none;
  font-size: 14px;
  line-height: 1.6;
  color: #333;
  background: transparent;
  font-family: inherit;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}

/* 智能体选择器 */
.agent-selector { position: relative; }

.agent-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: 1px solid #d0d7e3;
  border-radius: 20px;
  background: #f0f4ff;
  color: #3a5bd9;
  font-size: 13px;
  cursor: pointer;
  transition: background .2s;
}
.agent-btn:hover { background: #e0e8ff; }
.arrow { font-size: 10px; }

.agent-dropdown {
  position: absolute;
  bottom: calc(100% + 8px);
  left: 0;
  min-width: 180px;
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 4px 20px rgba(0,0,0,.12);
  padding: 6px 0;
  z-index: 100;
}

.agent-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 16px;
  font-size: 13px;
  cursor: pointer;
  color: #333;
}
.agent-option:hover { background: #f5f7ff; }
.agent-option.active { color: #409eff; font-weight: 600; }

.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #ccc;
  flex-shrink: 0;
}
.dot.on { background: #52c41a; }

.no-agent { padding: 12px 16px; font-size: 13px; color: #999; }
.no-agent a { color: #409eff; }

.clear-btn {
  margin-left: auto;
  background: none;
  border: none;
  font-size: 18px;
  color: #aaa;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
}
.clear-btn:hover { color: #666; background: #f0f0f0; }

.send-btn {
  padding: 7px 20px;
  background: #409eff;
  color: #fff;
  border: none;
  border-radius: 20px;
  font-size: 13px;
  cursor: pointer;
  transition: background .2s;
}
.send-btn:hover:not(:disabled) { background: #337ecc; }
.send-btn:disabled { background: #c0d8f5; cursor: not-allowed; }
</style>
