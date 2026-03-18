<template>
  <div class="skills-page">
    <div class="page-header">
      <div class="header-left">
        <div class="header-top">
          <button @click="goHome" class="back-btn" title="返回主页">
            <Home :size="18" />
          </button>
          <h1 class="page-title">
            <Zap :size="28" class="title-icon" />
            Skill 智能模块
          </h1>
        </div>
        <p class="page-subtitle">创建和管理智能技能，自动化知识处理流程</p>
      </div>
      <div class="header-actions">
        <button @click="showCreateModal = true" class="create-btn">
          <Plus :size="18" />
          创建 Skill
        </button>
      </div>
    </div>

    <div class="templates-section">
      <h2 class="section-title">
        <Package :size="18" class="title-icon" />
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
            <Sparkles :size="28" />
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
          <Rocket :size="18" class="title-icon" />
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
          <div class="card-content">
            <div class="card-header">
              <span class="skill-icon" :style="{ color: skill.color }">
                <Zap :size="24" />
              </span>
              <div class="skill-info">
                <h3 class="skill-name">{{ skill.name }}</h3>
                <span class="skill-type" :style="{ backgroundColor: skill.color + '20', color: skill.color }">
                  {{ skill.trigger_type === 'manual' ? '手动触发' : '定时执行' }}
                </span>
              </div>
              <div class="skill-actions">
                <button @click="toggleSkillStatus(skill)" class="action-btn" :title="skill.is_active ? '停用' : '启用'">
                  <Pause v-if="skill.is_active" :size="14" />
                  <Play v-else :size="14" />
                </button>
                <button @click="editSkill(skill)" class="action-btn" title="编辑">
                  <Edit3 :size="14" />
                </button>
                <button @click="deleteSkill(skill)" class="action-btn danger" title="删除">
                  <Trash2 :size="14" />
                </button>
              </div>
            </div>
            
            <p class="skill-description">{{ skill.description || '暂无描述' }}</p>
            
            <div class="card-footer">
              <div class="skill-meta">
                <span class="meta-item">
                  <BarChart3 :size="12" />
                  {{ skill.execution_count || 0 }} 次执行
                </span>
                <span class="meta-item">
                  <Calendar :size="12" />
                  {{ formatDate(skill.updated_at) }}
                </span>
              </div>
              <button @click="executeSkill(skill)" class="execute-btn" :disabled="!skill.is_active">
                <Play :size="14" />
                执行
              </button>
            </div>
          </div>
        </div>

        <div v-if="filteredSkills.length === 0" class="empty-state">
          <Zap :size="48" class="empty-icon" />
          <h3>暂无 Skill</h3>
          <p>从模板库选择或创建自定义 Skill</p>
        </div>
      </div>
    </div>

    <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>创建 Skill</h3>
          <button @click="showCreateModal = false" class="close-btn">
            <X :size="20" />
          </button>
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
                {{ cat.name }}
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
          <button @click="showExecuteModal = false" class="close-btn">
            <X :size="20" />
          </button>
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
import { 
  Home, Zap, Plus, Package, Sparkles, Rocket, Play, Pause,
  Edit3, Trash2, BarChart3, Calendar, X
} from 'lucide-vue-next'

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
  color: '#0066FF',
  trigger_type: 'manual',
  output_category_id: null as string | null
})

const colorOptions = [
  '#0066FF', '#f59e0b', '#10b981', '#ef4444',
  '#ec4899', '#8b5cf6', '#06b6d4', '#3b82f6'
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
    color: '#0066FF',
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
  background: var(--bg-primary);
  min-height: 100%;
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
  background: var(--bg-hover);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--text-secondary);
  transition: all 0.2s;

  &:hover {
    background: var(--bg-active);
    color: var(--text-primary);
  }
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--text-primary);
  
  .title-icon {
    color: var(--tech-blue);
  }
}

.page-subtitle {
  font-size: 14px;
  color: var(--text-muted);
}

.create-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  background: var(--primary-color);
  border: none;
  border-radius: var(--radius-md);
  color: #000;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  
  &:hover {
    background: var(--primary-hover);
    transform: translateY(-1px);
  }
}

.templates-section, .skills-section {
  margin-bottom: 32px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
  color: var(--text-primary);
  
  .title-icon {
    color: var(--tech-blue);
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
    background: var(--bg-hover);
    border: 1px solid var(--border-subtle);
    border-radius: 20px;
    color: var(--text-secondary);
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;
    
    &:hover {
      background: var(--bg-active);
    }
    
    &.active {
      background: var(--tech-blue-muted);
      border-color: var(--tech-blue);
      color: var(--tech-blue);
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
  background: var(--bg-tertiary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xl);
  cursor: pointer;
  transition: all 0.2s;
  
  &:hover {
    transform: translateY(-2px);
    border-color: var(--border-default);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
  }
  
  .template-icon {
    display: flex;
    align-items: center;
    justify-content: center;
  }
  
  .template-info {
    flex: 1;
  }
  
  .template-name {
    font-size: 15px;
    font-weight: 600;
    margin-bottom: 4px;
    color: var(--text-primary);
  }
  
  .template-desc {
    font-size: 12px;
    color: var(--text-muted);
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
  background: var(--bg-tertiary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xl);
  padding: 24px;
  transition: all 0.2s;
  
  &:hover {
    transform: translateY(-2px);
    border-color: var(--border-default);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
  }
  
  &.inactive {
    opacity: 0.6;
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
    display: flex;
    align-items: center;
    justify-content: center;
  }
  
  .skill-info {
    flex: 1;
  }
  
  .skill-name {
    font-size: 17px;
    font-weight: 600;
    margin-bottom: 6px;
    color: var(--text-primary);
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
      background: var(--bg-hover);
      border: none;
      border-radius: var(--radius-md);
      cursor: pointer;
      color: var(--text-secondary);
      transition: all 0.2s;
      
      &:hover {
        background: var(--bg-active);
        color: var(--text-primary);
      }
      
      &.danger:hover {
        background: rgba(239, 68, 68, 0.1);
        color: var(--accent-red);
      }
    }
  }
  
  .skill-description {
    font-size: 13px;
    color: var(--text-muted);
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
    color: var(--text-muted);
  }
  
  .execute-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    background: var(--primary-color);
    border: none;
    border-radius: var(--radius-md);
    color: #000;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    
    &:hover:not(:disabled) {
      background: var(--primary-hover);
      transform: translateY(-1px);
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
    color: var(--text-muted);
    margin-bottom: 16px;
    opacity: 0.5;
  }
  
  h3 {
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 8px;
    color: var(--text-secondary);
  }
  
  p {
    font-size: 14px;
    color: var(--text-muted);
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
  background: var(--bg-elevated);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-xl);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid var(--border-subtle);
  
  h3 {
    font-size: 18px;
    font-weight: 600;
    color: var(--text-primary);
  }
  
  .close-btn {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    
    &:hover {
      color: var(--text-primary);
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
    color: var(--text-secondary);
    margin-bottom: 8px;
  }
  
  input, textarea, select {
    width: 100%;
    padding: 10px 14px;
    background: var(--bg-hover);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    color: var(--text-primary);
    font-size: 14px;
    
    &:focus {
      outline: none;
      border-color: var(--tech-blue);
    }
    
    &::placeholder {
      color: var(--text-muted);
    }
  }
  
  textarea {
    resize: vertical;
    min-height: 80px;
  }
  
  select option {
    background: var(--bg-elevated);
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
    border-color: var(--text-primary);
  }
}

.execute-result {
  margin-top: 16px;
  padding: 16px;
  background: var(--bg-hover);
  border-radius: var(--radius-md);
  
  h4 {
    font-size: 13px;
    color: var(--text-secondary);
    margin-bottom: 8px;
  }
  
  pre {
    font-size: 12px;
    color: var(--tech-blue);
    white-space: pre-wrap;
    word-break: break-all;
  }
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 20px;
  border-top: 1px solid var(--border-subtle);
}

.btn-cancel, .btn-confirm {
  padding: 10px 20px;
  border-radius: var(--radius-md);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-cancel {
  background: transparent;
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  
  &:hover {
    background: var(--bg-hover);
  }
}

.btn-confirm {
  background: var(--primary-color);
  border: none;
  color: #000;
  font-weight: 500;
  
  &:hover:not(:disabled) {
    background: var(--primary-hover);
  }
  
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    gap: 16px;
  }
  
  .skills-grid, .templates-grid {
    grid-template-columns: 1fr;
  }
}
</style>
