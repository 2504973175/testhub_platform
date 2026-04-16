<template>
  <div class="login-container">
    <!-- 登录表单 -->
    <div class="login-section">
      <div class="login-form-wrapper">
        <div class="form-header">
          <h2>欢迎回来</h2>
          <p>登录以继续使用一站式智能化测试平台</p>
        </div>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          @submit.prevent="handleLogin"
          class="login-form"
        >
          <el-form-item prop="username">
            <el-input
              v-model="form.username"
              placeholder="请输入用户名"
              size="large"
              :prefix-icon="User"
            />
          </el-form-item>

          <el-form-item prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="请输入密码"
              size="large"
              :prefix-icon="Lock"
              show-password
              @keyup.enter="handleLogin"
            />
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              size="large"
              :loading="loading"
              @click="handleLogin"
              class="login-button"
            >
              <span v-if="!loading">登录</span>
              <span v-else>登录中...</span>
            </el-button>
          </el-form-item>

          <div class="form-footer">
            <router-link to="/register" class="register-link">
              还没有账号？<span>立即注册</span>
            </router-link>
          </div>
        </el-form>

       
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, h } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, Document, MagicStick, Connection, TrendCharts } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref()
const loading = ref(false)

const form = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ]
}

// 特性数据
const features = [
  {
    icon: Document,
    title: 'AI用例生成',
    description: '基于自然语言自动生成测试用例',
    color: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
  },
  {
    icon: MagicStick,
    title: 'AI智能测试',
    description: '智能分析需求，自动化执行测试',
    color: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)'
  },
  {
    icon: Connection,
    title: '多类型测试',
    description: '支持接口、UI自动化测试',
    color: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)'
  },
  {
    icon: TrendCharts,
    title: '数据分析',
    description: '实时监控测试覆盖率与质量指标',
    color: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)'
  }
]

const handleLogin = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        console.log('开始登录...')
        const result = await userStore.login(form)
        console.log('登录结果:', result)
        console.log('用户store状态:', {
          token: userStore.token,
          user: userStore.user,
          isAuthenticated: userStore.isAuthenticated
        })

        ElMessage.success('登录成功')
        console.log('准备跳转到 /home')

        // 使用replace而不是push，避免返回登录页
        await router.replace('/ai-generation/requirement-analysis')
        console.log('跳转完成')

      } catch (error) {
        console.error('登录失败:', error)
        ElMessage.error(error.response?.data?.error || '登录失败')
      } finally {
        loading.value = false
      }
    }
  })
}
</script>

<style lang="scss" scoped>
.login-container {
  height: 100vh;
  display: flex;
  background: #f5f7fa url('@/assets/login-bg.png') center center / cover no-repeat;
  overflow: hidden;
  align-items: center;
  justify-content: center;
}

/* 右侧登录表单 */
.login-section {
  width: 460px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: white;
  padding: 60px;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0,0,0,.08);
  position: relative;

  .login-form-wrapper {
    width: 100%;
    max-width: 400px;
  }

  .form-header {
    text-align: center;
    margin-bottom: 40px;
    animation: fadeIn 0.8s ease-out;

    h2 {
      font-size: 28px;
      font-weight: 700;
      color: #303133;
      margin: 0 0 12px 0;
    }

    p {
      font-size: 14px;
      color: #909399;
      margin: 0;
      line-height: 1.6;
    }
  }

  .login-form {
    :deep(.el-input__wrapper) {
      padding: 8px 16px;
      box-shadow: 0 0 0 1px #dcdfe6 inset;
      transition: all 0.3s ease;

      &:hover {
        box-shadow: 0 0 0 1px #c0c4cc inset;
      }

      &.is-focus {
        box-shadow: 0 0 0 1px #667eea inset;
      }
    }

    :deep(.el-form-item) {
      margin-bottom: 24px;
    }

    .login-button {
      width: 100%;
      height: 48px;
      font-size: 16px;
      font-weight: 600;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      border: none;
      transition: all 0.3s ease;

      &:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
      }

      &:active {
        transform: translateY(0);
      }
    }
  }

  .form-footer {
    text-align: center;
    margin-top: 24px;

    .register-link {
      color: #909399;
      text-decoration: none;
      font-size: 14px;
      transition: all 0.3s ease;

      span {
        color: #667eea;
        font-weight: 600;
      }

      &:hover {
        color: #667eea;
      }
    }
  }

  .bottom-info {
    margin-top: 60px;
    text-align: center;

    p {
      font-size: 12px;
      color: #c0c4cc;
      margin: 0;
    }
  }
}

/* 动画 */
@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes fadeInDown {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes float {
  0%, 100% {
    transform: translate(0, 0) rotate(0deg);
  }
  25% {
    transform: translate(30px, -30px) rotate(90deg);
  }
  50% {
    transform: translate(-20px, 20px) rotate(180deg);
  }
  75% {
    transform: translate(20px, 10px) rotate(270deg);
  }
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .showcase-section {
    padding: 40px;

    .features-grid {
      grid-template-columns: 1fr;
    }
  }
}

@media (max-width: 768px) {
  .login-container {
    flex-direction: column;
  }

  .showcase-section {
    min-height: 50vh;
    padding: 30px;

    .brand-header {
      margin-bottom: 30px;

      .logo-wrapper .brand-title {
        font-size: 32px;
      }
    }

    .features-grid {
      display: none;
    }
  }

  .login-section {
    width: 100%;
    padding: 30px;
  }
}
</style>
