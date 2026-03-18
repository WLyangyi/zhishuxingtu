<template>
  <div class="skills-page">
    <div class="page-header">
      <div class="header-left">
        <div class="header-top">
          <button @click="goHome" class="back-btn" title="返回主页">
            <span>🏠</span>
          </button>
          <h1 class="page-title">
            <span class="title-icon">⚡</span>
            Skill 智能模块
          </h1>
        </div>
        <p class="page-subtitle">创建和管理智能技能，自动化知识处理流程</p>
      </div>
      <div class="header-actions">
        <button @click="showCreateModal = true" class="create-btn">
          <span class="btn-icon">+</span>
          创建 Skill
        </button>
      </div>
    </div>

    <div class="templates-section">
      <h2 class="section-title">
        <span class="title-icon">📦</span>
        模板库
      </h2>
      <div class="templates-grid">
        <div 
          v-for="(template, index) in templates" 
          :key="index"
          class="template-card"
          @click="createFromTemplate(index)"
        >
          <div class="template-icon" :style="{ color: template.color }">
            {{ template.icon }}
          </div>
          <div class="template-info">
            <h3 class="template-name">{{ template.name }}</h3>
            <p class="template-desc">{{ template.description }}</p>
          </div>
          <div class="template-badge" :style="{ backgroundColor: template.color + '20', color: template.color }">
            {{ template.trigger_type === 'manual' ? '手动' : '定时' }}
          </div>
        </div>
      </div>
    </div>

    <div class="skills-section">
      <div class="section-header">
        <h2 class="section-title">
          <span class="title-icon">🚀</span>
          我的 Skills
        </h2>
        <div class="filter-tabs">
          <button 
            :class="{ active: filterType === 'all' }"
            @click="filterType = 'all'"
          >
            全部
          </button>
          <button 
            :class="{ active: filterType === 'manual' }"
            @click="filterType = 'manual'"
          >
            手动
          </button>
          <button 
            :class="{ active: filterType === 'scheduled' }"
            @click="filterType = 'scheduled'"
          >
            定时
          </button>
        </div>
      </div>

      <div class="skills-grid">
        <div 
          v-for="skill in filteredSkills" 
          :key="skill.id"
          class="skill-card"
          :class="{ inactive: !skill.is_active }"
        >
          <div class="card-glow"></div>
          <div class="card-content">
            <div class="card-header">
              <span class="skill-icon" :style="{ color: skill.color }">
                {{ skill.icon }}
              </span>
              <div class="skill-info">
                <h3 class="skill-name">{{ skill.name }}</h3>
                <span class="skill-type" :style="{ backgroundColor: skill.color + '20', color: skill.color }">
                  {{ skill.trigger_type === 'manual' ? '手动触发' : '定时执行' }}
                </span>
              </div>
              <div class="skill-actions">
                <button @click="toggleSkillStatus(skill)" class="action-btn" :title="skill.is_active ? '停用' : '启用'">
                  {{ skill.is_active ? '⏸️' : '▶️' }}
                </button>
                <button @click="editSkill(skill)" class="action-btn" title="编辑">
                  ✏️
                </button>
                <button @click="deleteSkill(skill)" class="action-btn danger" title="删除">
                  🗑️
                </button>
              </div>
            </div>
            
            <p class="skill-description">{{ skill.description || '暂无描述' }}</p>
            
            <div class="card-footer">
              <div class="skill-meta">
                <span class="meta-item">
                  <span class="meta-icon">📊</span>
                  {{ skill.execution_count || 0 }} 次执行
                </span>
                <span class="meta-item">
                  <span class="meta-icon">📅</span>
                  {{ formatDate(skill.updated_at) }}
                </span>
              </div>
              <button @click="executeSkill(skill)" class="execute-btn" :disabled="!skill.is_active">
                <span class="btn-icon">▶</span>
                执行
              </button>
            </div>
          </div>
        </div>

        <div v-if="filteredSkills.length === 0" class="empty-state">
          <div class="empty-icon">⚡</div>
          <h3>暂无 Skill</h3>
          <p>从模板库选择或创建自定义 Skill</p>
        </div>
      </div>
    </div>

    <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>创建 Skill</h3>
          <button @click="showCreateModal = false" class="close-btn">×</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>Skill 名称</label>
            <input v-model="newSkill.name" type="text" placeholder="输入 Skill 名称" />
          </div>
          <div class="form-group">
            <label>描述</label>
            <textarea v-model="newSkill.description" placeholder="描述这个 Skill 的功能"></textarea>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>图标</label>
              <input v-model="newSkill.icon" type="text" placeholder="如：⚡" />
            </div>
            <div class="form-group">
              <label>颜色</label>
              <div class="color-picker">
                <span 
                  v-for="color in colorOptions" 
                  :key="color"
                  class="color-dot"
                  :class="{ active: newSkill.color === color }"
                  :style="{ backgroundColor: color }"
                  @click="newSkill.color = color"
                />
              </div>
            </div>
          </div>
          <div class="form-group">
            <label>触发类型</label>
            <select v-model="newSkill.trigger_type">
              <option value="manual">手动触发</option>
              <option value="scheduled">定时执行</option>
            </select>
          </div>
          <div class="form-group">
            <label>输出分类</label>
            <select v-model="newSkill.output_category_id">
              <option :value="null">不保存到知识库</option>
              <option v-for="cat in categoryStore.categories" :key="cat.id" :value="cat.id">
                {{ cat.icon }} {{ cat.name }}
              </option>
            </select>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="showCreateModal = false" class="btn-cancel">取消</button>
          <button @click="handleCreateSkill" class="btn-confirm">创建</button>
        </div>
      </div>
    </div>

    <div v-if="showExecuteModal" class="modal-overlay" @click.self="showExecuteModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>执行 Skill: {{ currentSkill?.name }}</h3>
          <button @click="showExecuteModal = false" class="close-btn">×</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>输入数据 (JSON 格式)</label>
            <textarea 
              v-model="executeInput" 
              placeholder='{"key": "value"}'
              rows="6"
            ></textarea>
          </div>
          <div v-if="executeResult" class="execute-result">
            <h4>执行结果</h4>
            <pre>{{ JSON.stringify(executeResult, null, 2) }}</pre>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="showExecuteModal = false" class="btn-cancel">关闭</button>
          <button @click="handleExecuteSkill" class="btn-confirm" :disabled="executing">
            {{ executing ? '执行中...' : '执行' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCategoryStore } from '@/stores/category'
import { useNotificationStore } from '@/stores/notification'
import { skillsApi } from '@/api/skills'
import type { Skill, SkillTemplate } from '@/types/skill'

const router = useRouter()
const categoryStore = useCategoryStore()
const notification = useNotificationStore()

const templates = ref<SkillTemplate[]>([])
const skills = ref<Skill[]>([])
const filterType = ref<'all' | 'manual' | 'scheduled'>('all')
const showCreateModal = ref(false)
const showExecuteModal = ref(false)
const currentSkill = ref<Skill | null>(null)
const executeInput = ref('{}')
const executeResult = ref<any>(null)
const executing = ref(false)

const newSkill = ref({
  name: '',
  description: '',
  icon: '⚡',
  color: '#00d4ff',
  trigger_type: 'manual',
  output_category_id: null as string | null
})

const colorOptions = [
  '#00d4ff', '#7b2cbf', '#10b981', '#f59e0b',
  '#ef4444', '#ec4899', '#8b5cf6', '#06b6d4'
]

const filteredSkills = computed(() => {
  if (filterType.value === 'all') return skills.value
  return skills.value.filter(s => s.trigger_type === filterType.value)
})

onMounted(async () => {
  await Promise.all([
    loadTemplates(),
    loadSkills(),
    categoryStore.fetchCategories()
  ])
})

async function loadTemplates() {
  try {
    templates.value = await skillsApi.getTemplates()
  } catch (e) {
    console.error(e)
  }
}

async function loadSkills() {
  try {
    const response = await skillsApi.getSkills()
    skills.value = response.items
  } catch (e) {
    console.error(e)
  }
}

async function createFromTemplate(index: number) {
  try {
    const skill = await skillsApi.createFromTemplate(index)
    skills.value.unshift(skill as any)
    notification.success('Skill 创建成功', `「${skill.name}」已添加`)
  } catch (e: any) {
    notification.error('创建失败', e.response?.data?.detail || '操作失败')
  }
}

async function handleCreateSkill() {
  if (!newSkill.value.name.trim()) {
    notification.warning('请输入 Skill 名称')
    return
  }

  try {
    const skill = await skillsApi.createSkill({
      name: newSkill.value.name,
      description: newSkill.value.description,
      icon: newSkill.value.icon,
      color: newSkill.value.color,
      trigger_type: newSkill.value.trigger_type,
      output_category_id: newSkill.value.output_category_id || undefined
    })
    skills.value.unshift(skill as any)
    showCreateModal.value = false
    notification.success('Skill 创建成功')
    resetNewSkill()
  } catch (e: any) {
    notification.error('创建失败', e.response?.data?.detail || '操作失败')
  }
}

function resetNewSkill() {
  newSkill.value = {
    name: '',
    description: '',
    icon: '⚡',
    color: '#00d4ff',
    trigger_type: 'manual',
    output_category_id: null
  }
}

async function toggleSkillStatus(skill: Skill) {
  try {
    const updated = await skillsApi.updateSkill(skill.id, { is_active: !skill.is_active })
    const index = skills.value.findIndex(s => s.id === skill.id)
    if (index !== -1) {
      skills.value[index] = updated as any
    }
    notification.success(updated.is_active ? 'Skill 已启用' : 'Skill 已停用')
  } catch (e: any) {
    notification.error('操作失败', e.response?.data?.detail || '操作失败')
  }
}

function editSkill(_skill: Skill) {
  notification.info('功能开发中', 'Skill 编辑功能即将上线')
}

async function deleteSkill(skill: Skill) {
  if (!confirm(`确定要删除 Skill「${skill.name}」吗？`)) return

  try {
    await skillsApi.deleteSkill(skill.id)
    skills.value = skills.value.filter(s => s.id !== skill.id)
    notification.success('Skill 已删除')
  } catch (e: any) {
    notification.error('删除失败', e.response?.data?.detail || '操作失败')
  }
}

function executeSkill(skill: Skill) {
  currentSkill.value = skill
  executeInput.value = '{}'
  executeResult.value = null
  showExecuteModal.value = true
}

async function handleExecuteSkill() {
  if (!currentSkill.value) return

  let inputData = {}
  try {
    inputData = JSON.parse(executeInput.value)
  } catch (e) {
    notification.warning('输入数据格式错误', '请输入有效的 JSON 格式')
    return
  }

  executing.value = true
  try {
    const result = await skillsApi.executeSkill(currentSkill.value.id, { input_data: inputData })
    executeResult.value = result.output_data
    notification.success('Skill 执行成功')
  } catch (e: any) {
    notification.error('执行失败', e.response?.data?.detail || '操作失败')
  } finally {
    executing.value = false
  }
}

function formatDate(date: string): string {
  const d = new Date(date)
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

function goHome() {
  router.push('/')
}
</script>

<style scoped lang="scss">
.skills-page {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 32px;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.header-top {
  display: flex;
  align-items: center;
  gap: 12px;
}

.back-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 212, 255, 0.1);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 10px;
  cursor: pointer;
  font-size: 18px;
  transition: all 0.2s;

  &:hover {
    background: rgba(0, 212, 255, 0.2);
    border-color: #00d4ff;
  }
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 12px;
  
  .title-icon {
    font-size: 32px;
  }
}

.page-subtitle {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.5);
}

.create-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  background: linear-gradient(135deg, #00d4ff 0%, #7b2cbf 100%);
  border: none;
  border-radius: 12px;
  color: white;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(0, 212, 255, 0.3);
  }
  
  .btn-icon {
    font-size: 18px;
  }
}

.templates-section, .skills-section {
  margin-bottom: 32px;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
  
  .title-icon {
    font-size: 20px;
  }
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.filter-tabs {
  display: flex;
  gap: 8px;
  
  button {
    padding: 8px 16px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 20px;
    color: rgba(255, 255, 255, 0.6);
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;
    
    &:hover {
      background: rgba(255, 255, 255, 0.1);
    }
    
    &.active {
      background: rgba(0, 212, 255, 0.2);
      border-color: rgba(0, 212, 255, 0.4);
      color: #00d4ff;
    }
  }
}

.templates-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.template-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: linear-gradient(135deg, rgba(18, 18, 31, 0.9) 0%, rgba(26, 26, 46, 0.9) 100%);
  border: 1px solid rgba(0, 212, 255, 0.1);
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.3s;
  
  &:hover {
    transform: translateY(-4px);
    border-color: rgba(0, 212, 255, 0.3);
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
  }
  
  .template-icon {
    font-size: 32px;
  }
  
  .template-info {
    flex: 1;
  }
  
  .template-name {
    font-size: 15px;
    font-weight: 600;
    margin-bottom: 4px;
  }
  
  .template-desc {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.5);
  }
  
  .template-badge {
    padding: 4px 10px;
    border-radius: 10px;
    font-size: 11px;
    font-weight: 500;
  }
}

.skills-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.skill-card {
  position: relative;
  background: linear-gradient(135deg, rgba(18, 18, 31, 0.9) 0%, rgba(26, 26, 46, 0.9) 100%);
  border: 1px solid rgba(0, 212, 255, 0.1);
  border-radius: 14px;
  padding: 24px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  
  &:hover {
    transform: translateY(-4px);
    border-color: rgba(0, 212, 255, 0.3);
    
    .card-glow {
      opacity: 1;
    }
  }
  
  &.inactive {
    opacity: 0.6;
  }
  
  .card-glow {
    position: absolute;
    inset: 0;
    background: radial-gradient(
      400px circle at var(--mouse-x, 50%) var(--mouse-y, 50%),
      rgba(0, 212, 255, 0.08),
      transparent 40%
    );
    opacity: 0;
    transition: opacity 0.4s;
    pointer-events: none;
    border-radius: 14px;
  }
  
  .card-content {
    position: relative;
    z-index: 1;
  }
  
  .card-header {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 12px;
  }
  
  .skill-icon {
    font-size: 28px;
  }
  
  .skill-info {
    flex: 1;
  }
  
  .skill-name {
    font-size: 17px;
    font-weight: 600;
    margin-bottom: 6px;
  }
  
  .skill-type {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 10px;
    font-size: 11px;
    font-weight: 500;
  }
  
  .skill-actions {
    display: flex;
    gap: 6px;
    
    .action-btn {
      width: 28px;
      height: 28px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(255, 255, 255, 0.05);
      border: none;
      border-radius: 8px;
      cursor: pointer;
      font-size: 14px;
      transition: all 0.2s;
      
      &:hover {
        background: rgba(0, 212, 255, 0.2);
      }
      
      &.danger:hover {
        background: rgba(239, 68, 68, 0.2);
      }
    }
  }
  
  .skill-description {
    font-size: 13px;
    color: rgba(255, 255, 255, 0.5);
    line-height: 1.6;
    margin-bottom: 16px;
  }
  
  .card-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .skill-meta {
    display: flex;
    gap: 16px;
  }
  
  .meta-item {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: rgba(255, 255, 255, 0.4);
    
    .meta-icon {
      font-size: 12px;
    }
  }
  
  .execute-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    background: linear-gradient(135deg, #00d4ff 0%, #7b2cbf 100%);
    border: none;
    border-radius: 10px;
    color: white;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.3s;
    
    &:hover:not(:disabled) {
      transform: translateY(-2px);
      box-shadow: 0 4px 15px rgba(0, 212, 255, 0.3);
    }
    
    &:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
  }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px;
  text-align: center;
  
  .empty-icon {
    font-size: 48px;
    margin-bottom: 16px;
    opacity: 0.5;
  }
  
  h3 {
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 8px;
    color: rgba(255, 255, 255, 0.6);
  }
  
  p {
    font-size: 14px;
    color: rgba(255, 255, 255, 0.3);
  }
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  width: 500px;
  max-height: 80vh;
  overflow-y: auto;
  background: rgba(18, 18, 31, 0.98);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 16px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid rgba(0, 212, 255, 0.1);
  
  h3 {
    font-size: 18px;
    font-weight: 600;
  }
  
  .close-btn {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: none;
    color: rgba(255, 255, 255, 0.5);
    font-size: 24px;
    cursor: pointer;
    
    &:hover {
      color: #fff;
    }
  }
}

.modal-body {
  padding: 20px;
}

.form-group {
  margin-bottom: 16px;
  
  label {
    display: block;
    font-size: 13px;
    color: rgba(255, 255, 255, 0.6);
    margin-bottom: 8px;
  }
  
  input, textarea, select {
    width: 100%;
    padding: 10px 14px;
    background: rgba(0, 0, 0, 0.2);
    border: 1px solid rgba(0, 212, 255, 0.2);
    border-radius: 10px;
    color: #fff;
    font-size: 14px;
    
    &:focus {
      outline: none;
      border-color: #00d4ff;
    }
    
    &::placeholder {
      color: rgba(255, 255, 255, 0.3);
    }
  }
  
  textarea {
    resize: vertical;
    min-height: 80px;
  }
  
  select option {
    background: #1a1a2e;
  }
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.color-picker {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.color-dot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  cursor: pointer;
  border: 2px solid transparent;
  transition: all 0.2s;
  
  &:hover {
    transform: scale(1.15);
  }
  
  &.active {
    border-color: #fff;
    box-shadow: 0 0 10px currentColor;
  }
}

.execute-result {
  margin-top: 16px;
  padding: 16px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 10px;
  
  h4 {
    font-size: 13px;
    color: rgba(255, 255, 255, 0.6);
    margin-bottom: 8px;
  }
  
  pre {
    font-size: 12px;
    color: #00d4ff;
    white-space: pre-wrap;
    word-break: break-all;
  }
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 20px;
  border-top: 1px solid rgba(0, 212, 255, 0.1);
}

.btn-cancel, .btn-confirm {
  padding: 10px 20px;
  border-radius: 10px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-cancel {
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: rgba(255, 255, 255, 0.7);
  
  &:hover {
    background: rgba(255, 255, 255, 0.05);
  }
}

.btn-confirm {
  background: linear-gradient(135deg, #00d4ff 0%, #7b2cbf 100%);
  border: none;
  color: white;
  
  &:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 4px 15px rgba(0, 212, 255, 0.3);
  }
  
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}
</style>
