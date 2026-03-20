<template>
  <div class="prompt-lab-page">
    <div class="page-header">
      <div class="header-left">
        <div class="header-top">
          <button @click="goHome" class="back-btn" title="返回主页">
            <Home :size="18" />
          </button>
          <h1 class="page-title">
            <FlaskConical :size="28" class="title-icon" />
            提示词实验室
          </h1>
        </div>
        <p class="page-subtitle">管理和优化 AI 提示词质量</p>
      </div>
    </div>

    <div class="tabs-container">
      <div class="tabs-header">
        <div class="filter-tabs">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            :class="{ active: activeTab === tab.key }"
            @click="activeTab = tab.key"
          >
            <component :is="tab.icon" :size="16" />
            {{ tab.label }}
          </button>
        </div>
      </div>

      <div class="tab-content">
        <div v-show="activeTab === 'examples'" class="tab-panel">
          <div class="section-header">
            <h2 class="section-title">
              <BookOpen :size="18" class="title-icon" />
              Few-Shot 示例库
            </h2>
            <div class="section-actions">
              <select v-model="filterScenario" class="filter-select">
                <option value="">全场景</option>
                <option v-for="s in SCENARIOS" :key="s.value" :value="s.value">{{ s.label }}</option>
              </select>
              <button @click="showExampleModal = true" class="create-btn">
                <Plus :size="18" />
                添加示例
              </button>
            </div>
          </div>

          <div class="examples-grid">
            <div v-for="example in filteredExamples" :key="example.id" class="example-card">
              <div class="card-header">
                <span class="scenario-badge">{{ getScenarioLabel(example.scenario) }}</span>
                <div class="card-actions">
                  <button @click="editExample(example)" class="action-btn" title="编辑">
                    <Edit3 :size="14" />
                  </button>
                  <button @click="deleteExample(example)" class="action-btn danger" title="删除">
                    <Trash2 :size="14" />
                  </button>
                </div>
              </div>
              <div class="example-content">
                <div class="example-section">
                  <span class="example-label">输入：</span>
                  <p class="example-text">{{ truncateText(example.input_example, 100) }}</p>
                </div>
                <div class="example-section">
                  <span class="example-label">输出：</span>
                  <p class="example-text">{{ truncateText(example.output_example, 100) }}</p>
                </div>
              </div>
              <div class="card-footer">
                <span class="quality-score">
                  <Star :size="12" />
                  {{ example.quality_score.toFixed(1) }}
                </span>
              </div>
            </div>
            <div v-if="filteredExamples.length === 0" class="empty-state">
              <BookOpen :size="48" class="empty-icon" />
              <h3>暂无示例</h3>
              <p>添加 Few-Shot 示例来提升 AI 输出质量</p>
            </div>
          </div>
        </div>

        <div v-show="activeTab === 'abtest'" class="tab-panel">
          <div class="section-header">
            <h2 class="section-title">
              <GitCompare :size="18" class="title-icon" />
              A/B 测试
            </h2>
            <div class="section-actions">
              <select v-model="filterStatus" class="filter-select">
                <option value="">全部状态</option>
                <option value="running">运行中</option>
                <option value="paused">已暂停</option>
                <option value="completed">已完成</option>
              </select>
              <button @click="showExperimentModal = true" class="create-btn">
                <Plus :size="18" />
                创建实验
              </button>
            </div>
          </div>

          <div class="experiments-grid">
            <div v-for="exp in filteredExperiments" :key="exp.id" class="experiment-card">
              <div class="card-header">
                <h3 class="experiment-name">{{ exp.name }}</h3>
                <span class="status-badge" :class="exp.status">{{ getStatusLabel(exp.status) }}</span>
              </div>
              <p class="experiment-desc">{{ exp.description || '暂无描述' }}</p>
              <div class="experiment-stats">
                <div class="stat-item">
                  <span class="stat-label">流量分配</span>
                  <span class="stat-value">{{ (exp.traffic_split * 100).toFixed(0) }}% / {{ ((1 - exp.traffic_split) * 100).toFixed(0) }}%</span>
                </div>
              </div>
              <div class="card-footer">
                <button v-if="exp.status === 'running'" @click="pauseExperiment(exp)" class="action-btn">
                  <Pause :size="14" />
                  暂停
                </button>
                <button v-else-if="exp.status === 'paused'" @click="startExperiment(exp)" class="action-btn">
                  <Play :size="14" />
                  启动
                </button>
                <button @click="viewStats(exp)" class="action-btn primary">
                  <BarChart3 :size="14" />
                  统计
                </button>
              </div>
            </div>
            <div v-if="filteredExperiments.length === 0" class="empty-state">
              <GitCompare :size="48" class="empty-icon" />
              <h3>暂无实验</h3>
              <p>创建 A/B 实验来测试不同提示词版本的效果</p>
            </div>
          </div>
        </div>

        <div v-show="activeTab === 'cot'" class="tab-panel">
          <div class="section-header">
            <h2 class="section-title">
              <Brain :size="18" class="title-icon" />
              思维链模板
            </h2>
          </div>

          <div class="cot-grid">
            <div v-for="template in COT_TEMPLATES" :key="template.type" class="cot-card">
              <div class="cot-icon">
                <Lightbulb :size="32" />
              </div>
              <h3 class="cot-name">{{ template.name }}</h3>
              <p class="cot-desc">{{ template.description }}</p>
              <div class="cot-preview">
                <pre class="cot-code">{{ getCotPreview(template.type) }}</pre>
              </div>
              <button
                @click="applyCotTemplate(template)"
                class="apply-btn"
                :class="{ active: selectedCotType === template.type }"
              >
                {{ selectedCotType === template.type ? '已选择' : '使用此模板' }}
              </button>
            </div>
          </div>

          <div v-if="selectedCotType" class="cot-active-info">
            <CheckCircle :size="16" />
            当前选择：{{ COT_TEMPLATES.find(t => t.type === selectedCotType)?.name }}
          </div>
        </div>

        <div v-show="activeTab === 'chains'" class="tab-panel">
          <div class="section-header">
            <h2 class="section-title">
              <Workflow :size="18" class="title-icon" />
              提示词链
            </h2>
            <div class="section-actions">
              <button @click="showChainModal = true" class="create-btn">
                <Plus :size="18" />
                从预设创建
              </button>
            </div>
          </div>

          <div class="presets-section">
            <h3 class="subsection-title">预设链模板</h3>
            <div class="presets-grid">
              <div v-for="preset in presetChains" :key="preset.type" class="preset-card" @click="createFromPreset(preset.type)">
                <div class="preset-icon">
                  <Zap :size="24" />
                </div>
                <div class="preset-info">
                  <h4>{{ preset.name }}</h4>
                  <p>{{ preset.description }}</p>
                </div>
                <span class="step-count">{{ preset.steps.length }} 步</span>
              </div>
            </div>
          </div>

          <div class="chains-section">
            <h3 class="subsection-title">我的链</h3>
            <div class="chains-grid">
              <div v-for="chain in chains" :key="chain.id" class="chain-card">
                <div class="card-header">
                  <h3 class="chain-name">{{ chain.name }}</h3>
                  <span class="status-dot" :class="{ active: chain.is_active }"></span>
                </div>
                <p class="chain-desc">{{ chain.description || '暂无描述' }}</p>
                <div class="chain-steps">
                  <span v-for="(step, idx) in chain.steps" :key="idx" class="step-badge">
                    {{ idx + 1 }}. {{ step.step_name }}
                  </span>
                </div>
                <div class="card-footer">
                  <button @click="executeChain(chain)" class="execute-btn" :disabled="!chain.is_active">
                    <Play :size="14" />
                    执行
                  </button>
                </div>
              </div>
              <div v-if="chains.length === 0" class="empty-state small">
                <Workflow :size="36" class="empty-icon" />
                <p>暂无自定义链</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showExampleModal" class="modal-overlay" @click.self="closeExampleModal">
      <div class="modal modal-large">
        <div class="modal-header">
          <h3>{{ editingExample ? '编辑示例' : '添加示例' }}</h3>
          <button @click="closeExampleModal" class="close-btn">
            <X :size="20" />
          </button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>场景</label>
            <select v-model="exampleForm.scenario">
              <option v-for="s in SCENARIOS" :key="s.value" :value="s.value">{{ s.label }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>输入示例</label>
            <textarea v-model="exampleForm.input_example" placeholder="输入示例内容..." rows="4"></textarea>
          </div>
          <div class="form-group">
            <label>输出示例</label>
            <textarea v-model="exampleForm.output_example" placeholder="期望的输出内容..." rows="4"></textarea>
          </div>
          <div class="form-group">
            <label>质量评分 (1-10)</label>
            <input v-model.number="exampleForm.quality_score" type="number" min="1" max="10" step="0.1" />
          </div>
        </div>
        <div class="modal-footer">
          <button @click="closeExampleModal" class="btn-cancel">取消</button>
          <button @click="handleSaveExample" class="btn-confirm">{{ editingExample ? '保存' : '创建' }}</button>
        </div>
      </div>
    </div>

    <div v-if="showExperimentModal" class="modal-overlay" @click.self="showExperimentModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>创建实验</h3>
          <button @click="showExperimentModal = false" class="close-btn">
            <X :size="20" />
          </button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>实验名称</label>
            <input v-model="experimentForm.name" type="text" placeholder="输入实验名称" />
          </div>
          <div class="form-group">
            <label>描述</label>
            <textarea v-model="experimentForm.description" placeholder="描述实验目的..." rows="3"></textarea>
          </div>
          <div class="form-group">
            <label>流量分配 A/B</label>
            <div class="traffic-slider">
              <input v-model.number="experimentForm.traffic_split" type="range" min="0.1" max="0.9" step="0.1" />
              <span>{{ (experimentForm.traffic_split * 100).toFixed(0) }}% / {{ ((1 - experimentForm.traffic_split) * 100).toFixed(0) }}%</span>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="showExperimentModal = false" class="btn-cancel">取消</button>
          <button @click="handleCreateExperiment" class="btn-confirm">创建</button>
        </div>
      </div>
    </div>

    <div v-if="showChainModal" class="modal-overlay" @click.self="showChainModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>从预设创建链</h3>
          <button @click="showChainModal = false" class="close-btn">
            <X :size="20" />
          </button>
        </div>
        <div class="modal-body">
          <div class="preset-list">
            <div v-for="preset in presetChains" :key="preset.type" class="preset-option" @click="createFromPreset(preset.type); showChainModal = false">
              <div class="preset-option-icon"><Zap :size="20" /></div>
              <div class="preset-option-info">
                <h4>{{ preset.name }}</h4>
                <p>{{ preset.description }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showExecuteModal" class="modal-overlay" @click.self="showExecuteModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>执行链: {{ currentChain?.name }}</h3>
          <button @click="showExecuteModal = false" class="close-btn">
            <X :size="20" />
          </button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>输入数据 (JSON)</label>
            <textarea v-model="chainInput" placeholder='{"content": "文章内容..."}' rows="6"></textarea>
          </div>
          <div v-if="chainOutput" class="execute-result">
            <h4>执行结果</h4>
            <pre>{{ chainOutput }}</pre>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="showExecuteModal = false" class="btn-cancel">关闭</button>
          <button @click="handleExecuteChain" class="btn-confirm" :disabled="executingChain">
            {{ executingChain ? '执行中...' : '执行' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="showStatsModal" class="modal-overlay" @click.self="showStatsModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>实验统计</h3>
          <button @click="showStatsModal = false" class="close-btn">
            <X :size="20" />
          </button>
        </div>
        <div class="modal-body">
          <div class="stats-overview">
            <div class="stats-header">
              <h4>{{ currentExperiment?.name }}</h4>
              <span class="status-badge" :class="currentExperiment?.status">{{ getStatusLabel(currentExperiment?.status || '') }}</span>
            </div>
            <div class="stats-grid">
              <div class="stats-card version-a">
                <h5>版本 A</h5>
                <div class="stats-number">{{ stats?.version_a_samples || 0 }}</div>
                <div class="stats-label">样本数</div>
                <div v-if="stats?.version_a_avg_feedback" class="stats-detail">
                  平均反馈: {{ stats.version_a_avg_feedback.toFixed(2) }}
                </div>
              </div>
              <div class="stats-card version-b">
                <h5>版本 B</h5>
                <div class="stats-number">{{ stats?.version_b_samples || 0 }}</div>
                <div class="stats-label">样本数</div>
                <div v-if="stats?.version_b_avg_feedback" class="stats-detail">
                  平均反馈: {{ stats.version_b_avg_feedback.toFixed(2) }}
                </div>
              </div>
            </div>
            <div class="total-samples">
              总样本数: {{ stats?.total_samples || 0 }}
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="showStatsModal = false" class="btn-cancel">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useNotificationStore } from '@/stores/notification'
import { promptLabApi } from '@/api/promptLab'
import {
  COT_TEMPLATES, SCENARIOS
} from '@/types/promptLab'
import type {
  FewShotExample, FewShotExampleCreate,
  ABExperiment, ABExperimentStats,
  PromptChain,
  CoTTemplate
} from '@/types/promptLab'
import {
  Home, FlaskConical, BookOpen, GitCompare, Brain, Workflow,
  Plus, Edit3, Trash2, Star, X, Play, Pause, BarChart3,
  Lightbulb, CheckCircle, Zap
} from 'lucide-vue-next'

const router = useRouter()
const notification = useNotificationStore()

const tabs = [
  { key: 'examples', label: '示例库', icon: BookOpen },
  { key: 'abtest', label: 'A/B测试', icon: GitCompare },
  { key: 'cot', label: '思维链', icon: Brain },
  { key: 'chains', label: '链编排', icon: Workflow }
]

const activeTab = ref('examples')

const examples = ref<FewShotExample[]>([])
const experiments = ref<ABExperiment[]>([])
const chains = ref<PromptChain[]>([])
const presetChains = ref<any[]>([])
const selectedCotType = ref<string | null>(null)

const filterScenario = ref('')
const filterStatus = ref('')

const showExampleModal = ref(false)
const showExperimentModal = ref(false)
const showChainModal = ref(false)
const showExecuteModal = ref(false)
const showStatsModal = ref(false)

const editingExample = ref<FewShotExample | null>(null)
const currentExperiment = ref<ABExperiment | null>(null)
const currentChain = ref<PromptChain | null>(null)
const stats = ref<ABExperimentStats | null>(null)

const chainInput = ref('{"content": ""}')
const chainOutput = ref('')
const executingChain = ref(false)

const exampleForm = ref<FewShotExampleCreate>({
  scenario: 'knowledge_qa',
  input_example: '',
  output_example: '',
  quality_score: 5.0
})

const experimentForm = ref({
  name: '',
  description: '',
  traffic_split: 0.5
})

const filteredExamples = computed(() => {
  if (!filterScenario.value) return examples.value
  return examples.value.filter(e => e.scenario === filterScenario.value)
})

const filteredExperiments = computed(() => {
  if (!filterStatus.value) return experiments.value
  return experiments.value.filter(e => e.status === filterStatus.value)
})

onMounted(async () => {
  await loadData()
})

async function loadData() {
  try {
    const [exps, chs, presets] = await Promise.all([
      promptLabApi.abTest.listExperiments(),
      promptLabApi.promptChain.list(),
      promptLabApi.promptChain.getPresets()
    ])
    experiments.value = exps
    chains.value = chs
    presetChains.value = presets
    await loadExamples()
  } catch (e) {
    console.error(e)
  }
}

async function loadExamples() {
  try {
    examples.value = await promptLabApi.fewShot.list()
  } catch (e) {
    console.error(e)
  }
}

function goHome() {
  router.push('/')
}

function getScenarioLabel(scenario: string): string {
  return SCENARIOS.find(s => s.value === scenario)?.label || scenario
}

function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    running: '运行中',
    paused: '已暂停',
    completed: '已完成'
  }
  return labels[status] || status
}

function truncateText(text: string, maxLength: number): string {
  if (!text) return ''
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

function getCotPreview(type: string): string {
  const previews: Record<string, string> = {
    step_by_step: '步骤1：理解问题\n步骤2：信息检索\n步骤3：推理分析\n步骤4：得出结论',
    compare_analyze: '1. 维度识别\n2. 信息提取\n3. 对比分析\n4. 综合评估',
    deep_reasoning: '1. 问题分解\n2. 假设生成\n3. 假设验证\n4. 结论推导'
  }
  return previews[type] || ''
}

function closeExampleModal() {
  showExampleModal.value = false
  editingExample.value = null
  exampleForm.value = {
    scenario: 'knowledge_qa',
    input_example: '',
    output_example: '',
    quality_score: 5.0
  }
}

function editExample(example: FewShotExample) {
  editingExample.value = example
  exampleForm.value = {
    scenario: example.scenario,
    input_example: example.input_example,
    output_example: example.output_example,
    quality_score: example.quality_score
  }
  showExampleModal.value = true
}

async function handleSaveExample() {
  try {
    if (editingExample.value) {
      await promptLabApi.fewShot.update(editingExample.value.id, exampleForm.value)
      notification.success('更新成功')
    } else {
      await promptLabApi.fewShot.create(exampleForm.value)
      notification.success('创建成功')
    }
    await loadExamples()
    closeExampleModal()
  } catch (e: any) {
    notification.error('操作失败', e.response?.data?.detail || '操作失败')
  }
}

async function deleteExample(example: FewShotExample) {
  if (!confirm(`确定要删除此示例吗？`)) return
  try {
    await promptLabApi.fewShot.delete(example.id)
    notification.success('删除成功')
    await loadExamples()
  } catch (e: any) {
    notification.error('删除失败', e.response?.data?.detail || '操作失败')
  }
}

async function handleCreateExperiment() {
  if (!experimentForm.value.name.trim()) {
    notification.warning('请输入实验名称')
    return
  }
  try {
    await promptLabApi.abTest.createExperiment({
      name: experimentForm.value.name,
      description: experimentForm.value.description,
      prompt_id: '',
      version_a_id: '',
      version_b_id: '',
      traffic_split: experimentForm.value.traffic_split
    } as any)
    notification.success('创建成功')
    experiments.value = await promptLabApi.abTest.listExperiments()
    showExperimentModal.value = false
    experimentForm.value = { name: '', description: '', traffic_split: 0.5 }
  } catch (e: any) {
    notification.error('创建失败', e.response?.data?.detail || '操作失败')
  }
}

async function startExperiment(exp: ABExperiment) {
  try {
    await promptLabApi.abTest.startExperiment(exp.id)
    notification.success('实验已启动')
    experiments.value = await promptLabApi.abTest.listExperiments()
  } catch (e: any) {
    notification.error('操作失败', e.response?.data?.detail || '操作失败')
  }
}

async function pauseExperiment(exp: ABExperiment) {
  try {
    await promptLabApi.abTest.pauseExperiment(exp.id)
    notification.success('实验已暂停')
    experiments.value = await promptLabApi.abTest.listExperiments()
  } catch (e: any) {
    notification.error('操作失败', e.response?.data?.detail || '操作失败')
  }
}

async function viewStats(exp: ABExperiment) {
  currentExperiment.value = exp
  try {
    stats.value = await promptLabApi.abTest.getStats(exp.id)
    showStatsModal.value = true
  } catch (e: any) {
    notification.error('获取统计失败', e.response?.data?.detail || '操作失败')
  }
}

function applyCotTemplate(template: CoTTemplate) {
  selectedCotType.value = template.type
  notification.success(`已选择思维链模板: ${template.name}`)
}

async function createFromPreset(type: string) {
  try {
    const chain = await promptLabApi.promptChain.createFromPreset(type)
    chains.value = await promptLabApi.promptChain.list()
    notification.success(`已创建: ${chain.name}`)
    showChainModal.value = false
  } catch (e: any) {
    notification.error('创建失败', e.response?.data?.detail || '操作失败')
  }
}

function executeChain(chain: PromptChain) {
  currentChain.value = chain
  chainInput.value = '{"content": ""}'
  chainOutput.value = ''
  showExecuteModal.value = true
}

async function handleExecuteChain() {
  if (!currentChain.value) return
  executingChain.value = true
  try {
    let inputData = {}
    try {
      inputData = JSON.parse(chainInput.value)
    } catch {
      notification.warning('请输入有效的 JSON 格式')
      executingChain.value = false
      return
    }
    const result = await promptLabApi.promptChain.execute(currentChain.value.id, inputData)
    if (result.success) {
      chainOutput.value = result.output || '执行完成'
      notification.success('执行成功')
    } else {
      notification.error('执行失败', result.error || '未知错误')
    }
  } catch (e: any) {
    notification.error('执行失败', e.response?.data?.detail || '操作失败')
  } finally {
    executingChain.value = false
  }
}
</script>

<style scoped lang="scss">
.prompt-lab-page {
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
  margin-bottom: 24px;
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
    color: var(--primary-color);
  }
}

.page-subtitle {
  font-size: 14px;
  color: var(--text-muted);
  margin-left: 48px;
}

.tabs-container {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xl);
  overflow: hidden;
}

.tabs-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-subtle);
}

.filter-tabs {
  display: flex;
  gap: 8px;

  button {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 18px;
    background: var(--bg-hover);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    color: var(--text-secondary);
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      background: var(--bg-active);
      color: var(--text-primary);
    }

    &.active {
      background: var(--primary-muted);
      border-color: var(--primary-color);
      color: var(--primary-color);
    }
  }
}

.tab-content {
  padding: 20px;
}

.tab-panel {
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--text-primary);

  .title-icon {
    color: var(--primary-color);
  }
}

.section-actions {
  display: flex;
  gap: 12px;
}

.filter-select {
  padding: 8px 12px;
  background: var(--bg-hover);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;

  &:focus {
    border-color: var(--primary-color);
    outline: none;
  }
}

.create-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  background: var(--primary-color);
  border: none;
  border-radius: var(--radius-md);
  color: #000;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: var(--primary-hover);
    transform: translateY(-1px);
  }
}

.examples-grid,
.experiments-grid,
.chains-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.example-card,
.experiment-card,
.chain-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 20px;
  transition: all 0.2s;

  &:hover {
    border-color: var(--border-default);
  }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.scenario-badge {
  padding: 4px 10px;
  background: var(--tech-blue-muted);
  color: var(--tech-blue);
  border-radius: 20px;
  font-size: 11px;
  font-weight: 500;
}

.status-badge {
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 500;

  &.running {
    background: rgba(16, 185, 129, 0.15);
    color: var(--accent-green);
  }

  &.paused {
    background: rgba(245, 158, 11, 0.15);
    color: var(--primary-color);
  }

  &.completed {
    background: rgba(139, 92, 246, 0.15);
    color: var(--accent-purple);
  }
}

.card-actions {
  display: flex;
  gap: 6px;
}

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

  &.primary {
    background: var(--primary-muted);
    color: var(--primary-color);

    &:hover {
      background: var(--primary-color);
      color: #000;
    }
  }
}

.example-content {
  margin-bottom: 12px;
}

.example-section {
  margin-bottom: 8px;
}

.example-label {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 500;
}

.example-text {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
  margin-top: 4px;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.quality-score {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--primary-color);
}

.experiment-name,
.chain-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.experiment-desc,
.chain-desc {
  font-size: 13px;
  color: var(--text-muted);
  margin-bottom: 12px;
}

.experiment-stats {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-label {
  font-size: 11px;
  color: var(--text-muted);
}

.stat-value {
  font-size: 13px;
  color: var(--text-primary);
  font-weight: 500;
}

.cot-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.cot-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xl);
  padding: 24px;
  text-align: center;
  transition: all 0.2s;

  &:hover {
    border-color: var(--border-default);
    transform: translateY(-2px);
  }
}

.cot-icon {
  width: 56px;
  height: 56px;
  margin: 0 auto 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--primary-muted);
  border-radius: 50%;
  color: var(--primary-color);
}

.cot-name {
  font-size: 17px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.cot-desc {
  font-size: 13px;
  color: var(--text-muted);
  margin-bottom: 16px;
}

.cot-preview {
  background: var(--bg-hover);
  border-radius: var(--radius-md);
  padding: 12px;
  margin-bottom: 16px;
  text-align: left;
}

.cot-code {
  font-size: 11px;
  color: var(--text-secondary);
  font-family: 'JetBrains Mono', monospace;
  white-space: pre-wrap;
  line-height: 1.6;
}

.apply-btn {
  padding: 10px 20px;
  background: var(--bg-hover);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: var(--bg-active);
    color: var(--text-primary);
  }

  &.active {
    background: var(--primary-color);
    border-color: var(--primary-color);
    color: #000;
  }
}

.cot-active-info {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 20px;
  padding: 12px;
  background: var(--primary-muted);
  border-radius: var(--radius-md);
  color: var(--primary-color);
  font-size: 13px;
  font-weight: 500;
}

.presets-section {
  margin-bottom: 32px;
}

.subsection-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 16px;
}

.presets-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}

.preset-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: var(--primary-color);
    background: var(--bg-hover);
  }
}

.preset-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--primary-muted);
  border-radius: var(--radius-md);
  color: var(--primary-color);
}

.preset-info {
  flex: 1;

  h4 {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 2px;
  }

  p {
    font-size: 12px;
    color: var(--text-muted);
  }
}

.step-count {
  font-size: 11px;
  color: var(--text-muted);
  padding: 4px 8px;
  background: var(--bg-hover);
  border-radius: 20px;
}

.chain-steps {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
}

.step-badge {
  padding: 4px 10px;
  background: var(--bg-hover);
  border-radius: 20px;
  font-size: 11px;
  color: var(--text-secondary);
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
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-muted);

  &.active {
    background: var(--accent-green);
  }
}

.empty-state {
  grid-column: 1 / -1;
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

  &.small {
    padding: 30px;

    .empty-icon {
      margin-bottom: 8px;
    }

    p {
      font-size: 13px;
    }
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

  &.modal-large {
    width: 700px;
  }
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
    background: var(--bg-secondary);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    color: var(--text-primary);
    font-size: 14px;

    &:focus {
      outline: none;
      border-color: var(--primary-color);
    }
  }

  textarea {
    resize: vertical;
    min-height: 80px;
    font-family: inherit;
  }

  select option {
    background: var(--bg-elevated);
  }
}

.traffic-slider {
  display: flex;
  align-items: center;
  gap: 16px;

  input[type="range"] {
    flex: 1;
    background: transparent;
  }

  span {
    font-size: 14px;
    color: var(--text-primary);
    font-weight: 500;
    min-width: 80px;
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

  &:hover {
    background: var(--primary-hover);
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.preset-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.preset-option {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: var(--bg-hover);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: var(--primary-color);
    background: var(--bg-active);
  }
}

.preset-option-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--primary-muted);
  border-radius: var(--radius-md);
  color: var(--primary-color);
}

.preset-option-info {
  flex: 1;

  h4 {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 4px;
  }

  p {
    font-size: 12px;
    color: var(--text-muted);
  }
}

.execute-result {
  margin-top: 16px;
  padding: 16px;
  background: var(--bg-hover);
  border-radius: var(--radius-md);

  h4 {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 8px;
  }

  pre {
    font-size: 12px;
    color: var(--text-secondary);
    white-space: pre-wrap;
    word-break: break-word;
    max-height: 300px;
    overflow-y: auto;
  }
}

.stats-overview {
  .stats-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;

    h4 {
      font-size: 16px;
      font-weight: 600;
      color: var(--text-primary);
    }
  }
}

.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}

.stats-card {
  padding: 20px;
  border-radius: var(--radius-lg);
  text-align: center;

  h5 {
    font-size: 12px;
    font-weight: 500;
    margin-bottom: 8px;
  }

  .stats-number {
    font-size: 32px;
    font-weight: 700;
    margin-bottom: 4px;
  }

  .stats-label {
    font-size: 11px;
    opacity: 0.7;
  }

  .stats-detail {
    font-size: 11px;
    margin-top: 8px;
    opacity: 0.8;
  }

  &.version-a {
    background: rgba(0, 102, 255, 0.1);
    color: var(--tech-blue);
  }

  &.version-b {
    background: rgba(139, 92, 246, 0.1);
    color: var(--accent-purple);
  }
}

.total-samples {
  text-align: center;
  font-size: 14px;
  color: var(--text-secondary);
  padding: 12px;
  background: var(--bg-hover);
  border-radius: var(--radius-md);
}
</style>
