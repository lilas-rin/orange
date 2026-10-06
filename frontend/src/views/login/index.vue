<template>
  <div class="login-page">
    <div class="login-bg"></div>
    <div class="login-card">
      <div class="login-head">
        <div class="logo">橙</div>
        <div>
          <h1>XX脐橙产销数据分析与智能决策平台</h1>
          <p>信丰脐橙 · 产销一体 · 数据驱动 · 智能决策</p>
        </div>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" size="large" @submit.prevent>
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" :prefix-icon="User" clearable />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            :prefix-icon="Lock"
            show-password
            @keyup.enter="onSubmit"
          />
        </el-form-item>
        <el-button type="primary" class="submit" :loading="loading" @click="onSubmit">
          登 录
        </el-button>
      </el-form>

      <div class="tips">
        <span>演示账号：admin / admin123（管理员）</span>
        <el-button link type="primary" @click="goScreen">进入数字大屏 →</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const formRef = ref<FormInstance>()
const loading = ref(false)
const form = reactive({ username: 'admin', password: 'admin123' })

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function onSubmit() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    try {
      await userStore.login(form.username, form.password)
      ElMessage.success('登录成功')
      const redirect = (route.query.redirect as string) || '/dashboard'
      router.replace(redirect)
    } finally {
      loading.value = false
    }
  })
}

function goScreen() {
  router.push('/screen')
}
</script>

<style scoped>
.login-page {
  position: relative;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: #0e2a1b;
}

.login-bg {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 18% 22%, rgba(255, 155, 60, 0.28), transparent 42%),
    radial-gradient(circle at 82% 78%, rgba(52, 168, 83, 0.35), transparent 46%),
    linear-gradient(135deg, #0e2a1b 0%, #123a25 55%, #0a2115 100%);
}

.login-card {
  position: relative;
  width: 440px;
  background: rgba(255, 255, 255, 0.98);
  border-radius: 16px;
  padding: 34px 36px 26px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.3);
}

.login-head {
  display: flex;
  gap: 14px;
  align-items: center;
  margin-bottom: 26px;
}

.logo {
  width: 52px;
  height: 52px;
  flex-shrink: 0;
  border-radius: 14px;
  background: linear-gradient(135deg, #ff9d3d, #ef7a12);
  color: #fff;
  font-size: 24px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-head h1 {
  font-size: 17px;
  margin: 0;
  color: #1f2733;
  line-height: 1.35;
}

.login-head p {
  font-size: 12px;
  color: #82909e;
  margin: 6px 0 0;
}

.submit {
  width: 100%;
  height: 44px;
  font-size: 16px;
  letter-spacing: 4px;
  background: linear-gradient(90deg, #2c8b4c, #1f7a3f);
  border: none;
}

.tips {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 18px;
  font-size: 12px;
  color: #9aa5b1;
}
</style>
