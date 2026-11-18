<template>
  <div class="prompt-lab-page">
    <PageHeader
      kicker="LAB · PROMPT LAB"
      title="提示词实验室"
      description="Few-Shot 示例、A/B 实验、思维链与提示词链的集中工作台。"
    />

    <div class="lab">
      <div class="lab__bar">
        <SegmentedControl
          :items="tabItems"
          :model-value="activeTab"
          aria-label="实验室分区"
          @update:model-value="activeTab = $event"
        />
        <span class="readout lab__count">{{ activeTabHint }}</span>
      </div>

      <div class="tab-content">
        <div v-show="activeTab === 'examples'" class="tab-panel">
          <div class="section-header">
            <div class="section-heading">
              <span class="readout">EXAMPLES</span>
            <h2 class="section-title">
              <BookOpen :size="18" class="title-icon" />
              Few-Shot 示例库
            </h2>
            </div>
            <div class="section-actions">
              <AppSelect
                :model-value="filterScenario"
                :options="scenarioOptions"
                placeholder="全场景"
                aria-label="按场景筛选"
                @update:model-value="filterScenario = $event"
              />
              <AppButton size="sm" @click="showExampleModal = true">
                <template #icon><Plus :size="14" /></template>
                添加示例
              </AppButton>
            </div>
          </div>

          <div class="examples-grid">
            <div v-for="example in filteredExamples" :key="example.id" class="example-card">
              <div class="card-header">
                <span class="scenario-badge">{{ getScenarioLabel(example.scenario) }}</span>
                <div class="card-actions">
                  <button @click="viewExampleDetail(example)" class="action-btn" title="查看详情">
                    <Eye :size="14" />
                  </button>
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
            <div class="section-heading">
              <span class="readout">A/B TEST</span>
            <h2 class="section-title">
              <GitCompare :size="18" class="title-icon" />
              A/B 测试
            </h2>
            </div>
            <div class="section-actions">
              <AppSelect
                :model-value="filterStatus"
                :options="statusOptions"
                placeholder="全部状态"
                aria-label="按状态筛选"
                @update:model-value="filterStatus = $event"
              />
              <AppButton size="sm" @click="showExperimentModal = true">
                <template #icon><Plus :size="14" /></template>
                创建实验
              </AppButton>
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
                <div class="footer-left">
                  <button v-if="exp.status === 'running'" @click="pauseExperiment(exp)" class="action-btn">
                    <Pause :size="14" />
                    暂停
                  </button>
                  <button v-else-if="exp.status === 'paused'" @click="startExperiment(exp)" class="action-btn">
                    <Play :size="14" />
                    启动
                  </button>
                </div>
                <div class="footer-right">
                  <button @click="editExperiment(exp)" class="action-btn" title="编辑">
                    <Edit3 :size="14" />
                  </button>
                  <button @click="viewStats(exp)" class="action-btn primary" title="统计">
                    <BarChart3 :size="14" />
                  </button>
                  <button @click="deleteExperiment(exp)" class="action-btn danger" title="删除">
                    <Trash2 :size="14" />
                  </button>
                </div>
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
            <div class="section-heading">
              <span class="readout">CHAIN OF THOUGHT</span>
            <h2 class="section-title">
              <Brain :size="18" class="title-icon" />
              思维链模板
            </h2>
            </div>
            <div class="section-actions">
              <AppButton v-if="selectedCotType" size="sm" variant="ghost" @click="showCotPreviewModal = true">
                <template #icon><Eye :size="14" /></template>
                查看完整模板
              </AppButton>
            </div>
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
            <button @click="showCotPreviewModal = true" class="preview-link">查看详情</button>
          </div>
        </div>

        <div v-show="activeTab === 'chains'" class="tab-panel">
          <div class="section-header">
            <div class="section-heading">
              <span class="readout">CHAINS</span>
            <h2 class="section-title">
              <Workflow :size="18" class="title-icon" />
              提示词链
            </h2>
            </div>
            <div class="section-actions">
              <AppButton size="sm" @click="showChainModal = true">
                <template #icon><Plus :size="14" /></template>
                从预设创建
              </AppButton>
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
                  <div class="footer-right">
                    <button @click="toggleChainStatus(chain)" class="action-btn" :title="chain.is_active ? '禁用' : '启用'">
                      <component :is="chain.is_active ? Pause : Play" :size="14" />
                    </button>
                    <button @click="editChain(chain)" class="action-btn" title="编辑">
                      <Edit3 :size="14" />
                    </button>
                    <button @click="deleteChain(chain)" class="action-btn danger" title="删除">
                      <Trash2 :size="14" />
                    </button>
                  </div>
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
            <textarea v-model="exampleForm.input_example" placeholder="输入示例内容..." rows="6"></textarea>
          </div>
          <div class="form-group">
            <label>输出示例</label>
            <textarea v-model="exampleForm.output_example" placeholder="期望的输出内容..." rows="6"></textarea>
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

    <div v-if="showExampleDetailModal" class="modal-overlay" @click.self="showExampleDetailModal = false">
      <div class="modal modal-large">
        <div class="modal-header">
          <h3>示例详情</h3>
          <button @click="showExampleDetailModal = false" class="close-btn">
            <X :size="20" />
          </button>
        </div>
        <div class="modal-body" v-if="currentExample">
          <div class="example-detail-header">
            <span class="scenario-badge">{{ getScenarioLabel(currentExample.scenario) }}</span>
            <span class="quality-score">
              <Star :size="14" />
              质量评分: {{ currentExample.quality_score.toFixed(1) }}
            </span>
          </div>
          <div class="example-detail-section">
            <h5>输入示例</h5>
            <pre class="example-detail-content">{{ currentExample.input_example }}</pre>
          </div>
          <div class="example-detail-section">
            <h5>输出示例</h5>
            <pre class="example-detail-content">{{ currentExample.output_example }}</pre>
          </div>
          <div class="example-detail-meta">
            <span>创建时间: {{ formatDate(currentExample.created_at) }}</span>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="showExampleDetailModal = false" class="btn-cancel">关闭</button>
          <button @click="editExample(currentExample!); showExampleDetailModal = false" class="btn-confirm">编辑</button>
        </div>
      </div>
    </div>

    <div v-if="showExperimentModal" class="modal-overlay" @click.self="closeExperimentModal">
      <div class="modal">
        <div class="modal-header">
          <h3>{{ editingExperiment ? '编辑实验' : '创建实验' }}</h3>
          <button @click="closeExperimentModal" class="close-btn">
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
          <button @click="closeExperimentModal" class="btn-cancel">取消</button>
          <button @click="handleSaveExperiment" class="btn-confirm">{{ editingExperiment ? '保存' : '创建' }}</button>
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

    <div v-if="showEditChainModal" class="modal-overlay" @click.self="closeEditChainModal">
      <div class="modal">
        <div class="modal-header">
          <h3>编辑链</h3>
          <button @click="closeEditChainModal" class="close-btn">
            <X :size="20" />
          </button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>链名称</label>
            <input v-model="chainForm.name" type="text" placeholder="输入链名称" />
          </div>
          <div class="form-group">
            <label>描述</label>
            <textarea v-model="chainForm.description" placeholder="描述链的用途..." rows="3"></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="closeEditChainModal" class="btn-cancel">取消</button>
          <button @click="handleSaveChain" class="btn-confirm">保存</button>
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

    <div v-if="showCotPreviewModal" class="modal-overlay" @click.self="showCotPreviewModal = false">
      <div class="modal modal-large">
        <div class="modal-header">
          <h3>思维链模板详情</h3>
          <button @click="showCotPreviewModal = false" class="close-btn">
            <X :size="20" />
          </button>
        </div>
        <div class="modal-body">
          <div v-if="selectedCotType" class="cot-detail">
            <h4 class="cot-detail-title">{{ COT_TEMPLATES.find(t => t.type === selectedCotType)?.name }}</h4>
            <p class="cot-detail-desc">{{ COT_TEMPLATES.find(t => t.type === selectedCotType)?.description }}</p>
            <div class="cot-detail-section">
              <h5>提示词模板</h5>
              <pre class="cot-full-template">{{ getCotFullTemplate(selectedCotType) }}</pre>
            </div>
            <div class="cot-detail-section">
              <h5>适用场景</h5>
              <ul class="cot-scenarios">
                <li v-for="scenario in getCotScenarios(selectedCotType)" :key="scenario">{{ scenario }}</li>
              </ul>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="showCotPreviewModal = false" class="btn-cancel">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useNotificationStore } from '@/stores/notification'
import { AppButton, AppSelect, PageHeader, SegmentedControl } from '@/components/ui'
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
  BookOpen, GitCompare, Brain, Workflow,
  Plus, Edit3, Trash2, Star, X, Play, Pause, BarChart3,
  Lightbulb, CheckCircle, Zap, Eye
} from 'lucide-vue-next'

const notification = useNotificationStore()

const tabItems = [
  { label: '示例库', value: 'examples' },
  { label: 'A/B 测试', value: 'abtest' },
  { label: '思维链', value: 'cot' },
  { label: '链编排', value: 'chains' }
]

const statusOptions = [
  { label: '全部状态', value: '' },
  { label: '运行中', value: 'running' },
  { label: '已暂停', value: 'paused' },
  { label: '已完成', value: 'completed' }
]

const activeTab = ref('examples')

const scenarioOptions = computed(() => [
  { label: '全场景', value: '' },
  ...SCENARIOS.map((item) => ({ label: item.label, value: item.value }))
])

const activeTabHint = computed(() => {
  const map: Record<string, string> = {
    examples: `${filteredExamples.value.length} 个示例`,
    abtest: `${filteredExperiments.value.length} 个实验`,
    cot: `${COT_TEMPLATES.length} 个模板`,
    chains: `${chains.value.length} 条链`
  }
  return map[activeTab.value] ?? ''
})

const examples = ref<FewShotExample[]>([])
const experiments = ref<ABExperiment[]>([])
const chains = ref<PromptChain[]>([])
const presetChains = ref<any[]>([])
const selectedCotType = ref<string | null>(null)

const filterScenario = ref('')
const filterStatus = ref('')

const showExampleModal = ref(false)
const showExampleDetailModal = ref(false)
const showExperimentModal = ref(false)
const showChainModal = ref(false)
const showExecuteModal = ref(false)
const showStatsModal = ref(false)
const showEditChainModal = ref(false)
const showCotPreviewModal = ref(false)

const editingExample = ref<FewShotExample | null>(null)
const editingExperiment = ref<ABExperiment | null>(null)
const editingChain = ref<PromptChain | null>(null)
const currentExample = ref<FewShotExample | null>(null)
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

const chainForm = ref({
  name: '',
  description: ''
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

function viewExampleDetail(example: FewShotExample) {
  currentExample.value = example
  showExampleDetailModal.value = true
}

function formatDate(dateStr: string): string {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function getCotPreview(type: string): string {
  const previews: Record<string, string> = {
    step_by_step: '步骤1：理解问题\n步骤2：信息检索\n步骤3：推理分析\n步骤4：得出结论',
    compare_analyze: '1. 维度识别\n2. 信息提取\n3. 对比分析\n4. 综合评估',
    deep_reasoning: '1. 问题分解\n2. 假设生成\n3. 假设验证\n4. 结论推导'
  }
  return previews[type] || ''
}

function getCotFullTemplate(type: string): string {
  const templates: Record<string, string> = {
    step_by_step: `请按以下步骤逐步分析和解决问题：

步骤1：理解问题
- 识别问题的核心需求
- 明确问题的边界条件
- 列出已知信息和未知信息

步骤2：信息检索
- 从知识库中检索相关信息
- 整理和归纳检索到的内容
- 标注信息来源

步骤3：推理分析
- 基于已知信息进行逻辑推理
- 分析可能的解决方案
- 评估各方案的优劣

步骤4：得出结论
- 综合分析结果
- 给出明确的答案或建议
- 说明推理过程和依据`,

    compare_analyze: `请按以下维度进行对比分析：

1. 维度识别
- 识别需要对比的对象
- 确定对比的关键维度
- 设定评估标准

2. 信息提取
- 从各维度提取对象特征
- 收集相关数据和信息
- 标注信息来源

3. 对比分析
- 逐维度进行对比
- 分析差异和相似点
- 评估优劣势

4. 综合评估
- 汇总对比结果
- 给出综合评价
- 提供建议或结论`,

    deep_reasoning: `请按以下步骤进行深度推理：

1. 问题分解
- 将复杂问题拆解为子问题
- 识别问题的层次结构
- 确定优先级

2. 假设生成
- 基于已知信息提出假设
- 列出可能的解释或方案
- 考虑边界情况

3. 假设验证
- 设计验证方法
- 收集验证数据
- 分析验证结果

4. 结论推导
- 综合验证结果
- 排除不合理假设
- 得出可靠结论`
  }
  return templates[type] || ''
}

function getCotScenarios(type: string): string[] {
  const scenarios: Record<string, string[]> = {
    step_by_step: [
      '复杂问题求解',
      '技术方案设计',
      '故障排查分析',
      '学习路径规划'
    ],
    compare_analyze: [
      '技术选型对比',
      '方案优劣分析',
      '产品功能对比',
      '竞品分析'
    ],
    deep_reasoning: [
      '根本原因分析',
      '决策支持',
      '风险评估',
      '战略规划'
    ]
  }
  return scenarios[type] || []
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

function closeExperimentModal() {
  showExperimentModal.value = false
  editingExperiment.value = null
  experimentForm.value = { name: '', description: '', traffic_split: 0.5 }
}

function editExperiment(exp: ABExperiment) {
  editingExperiment.value = exp
  experimentForm.value = {
    name: exp.name,
    description: exp.description || '',
    traffic_split: exp.traffic_split
  }
  showExperimentModal.value = true
}

async function handleSaveExperiment() {
  if (!experimentForm.value.name.trim()) {
    notification.warning('请输入实验名称')
    return
  }
  try {
    if (editingExperiment.value) {
      await promptLabApi.abTest.updateExperiment(editingExperiment.value.id, experimentForm.value)
      notification.success('更新成功')
    } else {
      await promptLabApi.abTest.createExperiment({
        name: experimentForm.value.name,
        description: experimentForm.value.description,
        prompt_id: '',
        version_a_id: '',
        version_b_id: '',
        traffic_split: experimentForm.value.traffic_split
      } as any)
      notification.success('创建成功')
    }
    experiments.value = await promptLabApi.abTest.listExperiments()
    closeExperimentModal()
  } catch (e: any) {
    notification.error('操作失败', e.response?.data?.detail || '操作失败')
  }
}

async function deleteExperiment(exp: ABExperiment) {
  if (!confirm(`确定要删除实验 "${exp.name}" 吗？`)) return
  try {
    await promptLabApi.abTest.deleteExperiment(exp.id)
    notification.success('删除成功')
    experiments.value = await promptLabApi.abTest.listExperiments()
  } catch (e: any) {
    notification.error('删除失败', e.response?.data?.detail || '操作失败')
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

function editChain(chain: PromptChain) {
  editingChain.value = chain
  chainForm.value = {
    name: chain.name,
    description: chain.description || ''
  }
  showEditChainModal.value = true
}

function closeEditChainModal() {
  showEditChainModal.value = false
  editingChain.value = null
  chainForm.value = { name: '', description: '' }
}

async function handleSaveChain() {
  if (!editingChain.value) return
  if (!chainForm.value.name.trim()) {
    notification.warning('请输入链名称')
    return
  }
  try {
    await promptLabApi.promptChain.update(editingChain.value.id, chainForm.value)
    notification.success('更新成功')
    chains.value = await promptLabApi.promptChain.list()
    closeEditChainModal()
  } catch (e: any) {
    notification.error('更新失败', e.response?.data?.detail || '操作失败')
  }
}

async function deleteChain(chain: PromptChain) {
  if (!confirm(`确定要删除链 "${chain.name}" 吗？`)) return
  try {
    await promptLabApi.promptChain.delete(chain.id)
    notification.success('删除成功')
    chains.value = await promptLabApi.promptChain.list()
  } catch (e: any) {
    notification.error('删除失败', e.response?.data?.detail || '操作失败')
  }
}

async function toggleChainStatus(chain: PromptChain) {
  try {
    await promptLabApi.promptChain.update(chain.id, { is_active: !chain.is_active })
    notification.success(chain.is_active ? '已禁用' : '已启用')
    chains.value = await promptLabApi.promptChain.list()
  } catch (e: any) {
    notification.error('操作失败', e.response?.data?.detail || '操作失败')
  }
}
</script>

<style scoped>
.prompt-lab-page {
  position: relative;
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 32px 48px 72px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.lab {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.lab__bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--line);
}

.lab__count {
  color: var(--t3);
}

.tab-panel {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

/* ---- 区块标题 ---- */
.section-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--line);
}

.section-heading {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-display);
  font-size: var(--fs-title-2);
  font-weight: 600;
  letter-spacing: -0.02em;
}

.section-title .title-icon {
  color: var(--t3);
}

.section-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.section-actions :deep(.select-field) {
  width: 150px;
}

/* ---- 卡片通用 ---- */
.example-card,
.experiment-card,
.cot-card,
.chain-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 16px;
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  background: var(--panel);
  transition: border-color var(--d-fast) var(--ease-out);
}

.example-card:hover,
.experiment-card:hover,
.cot-card:hover,
.chain-card:hover {
  border-color: var(--line-strong);
}

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.card-actions {
  display: flex;
  align-items: center;
  gap: 2px;
}

.action-btn {
  width: 26px;
  height: 26px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--r-sm);
  color: var(--t3);
  transition: color var(--d-fast) var(--ease-out), background var(--d-fast) var(--ease-out);
}

.action-btn:hover {
  color: var(--text);
  background: var(--panel-2);
}

.action-btn.primary:hover {
  color: var(--gold);
  background: var(--gold-soft);
}

.action-btn.danger:hover {
  color: var(--danger);
  background: var(--danger-soft);
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: auto;
  padding-top: 10px;
  border-top: 1px solid var(--line);
}

.footer-left,
.footer-right {
  display: flex;
  align-items: center;
  gap: 4px;
}

/* ---- 示例库 ---- */
.examples-grid,
.experiments-grid,
.chains-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 12px;
}

.example-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 2px 0 4px;
}

.example-section {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.example-label {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.06em;
  color: var(--t3);
}

.example-text {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  font-size: var(--fs-micro);
  line-height: 1.7;
  color: var(--t2);
  white-space: pre-wrap;
}

.scenario-badge,
.status-badge {
  flex: none;
  padding: 2px 8px;
  border: 1px solid var(--line-strong);
  border-radius: var(--r-pill);
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.05em;
  color: var(--t2);
}

.status-badge.running {
  border-color: var(--gold-line);
  background: var(--gold-soft);
  color: var(--gold);
}

.status-badge.completed {
  border-color: var(--line-strong);
  color: var(--success);
}

.quality-score {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--gold);
}

/* ---- A/B 实验 ---- */
.experiment-name {
  font-size: var(--fs-body);
  font-weight: 500;
  line-height: 1.4;
}

.experiment-desc {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  font-size: var(--fs-micro);
  line-height: 1.7;
  color: var(--t2);
}

.experiment-stats {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 2px 0;
}

.stat-item {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
}

.stat-label {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.05em;
  color: var(--t3);
}

.stat-value {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text);
}

/* ---- 思维链 ---- */
.cot-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(270px, 1fr));
  gap: 12px;
}

.cot-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--gold-line);
  border-radius: var(--r-sm);
  background: var(--gold-soft);
  color: var(--gold);
}

.cot-name {
  font-family: var(--font-display);
  font-size: var(--fs-body);
  font-weight: 600;
}

.cot-desc {
  font-size: var(--fs-micro);
  line-height: 1.7;
  color: var(--t2);
}

.cot-preview {
  max-height: 128px;
  padding: 8px 10px;
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  background: var(--bg);
  overflow: auto;
}

.cot-code {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 9.5px;
  line-height: 1.7;
  color: var(--t3);
  white-space: pre-wrap;
  word-break: break-word;
}

.apply-btn {
  height: 30px;
  margin-top: auto;
  border: 1px solid var(--line-strong);
  border-radius: var(--r-sm);
  font-size: var(--fs-micro);
  color: var(--t2);
  transition: color var(--d-fast) var(--ease-out), border-color var(--d-fast) var(--ease-out),
    background var(--d-fast) var(--ease-out);
}

.apply-btn:hover {
  border-color: var(--gold-line);
  color: var(--gold);
}

.apply-btn.active {
  border-color: var(--gold-line);
  background: var(--gold-soft);
  color: var(--gold);
}

.cot-active-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border: 1px solid var(--gold-line);
  border-radius: var(--r-sm);
  background: var(--gold-soft);
  font-size: var(--fs-micro);
  color: var(--t2);
}

.preview-link {
  margin-left: auto;
  color: var(--gold);
  font-size: var(--fs-micro);
  text-decoration: underline dotted;
}

/* ---- 链编排 ---- */
.presets-section,
.chains-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.subsection-title {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--t3);
}

.presets-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 10px;
}

.preset-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  cursor: pointer;
  transition: border-color var(--d-fast) var(--ease-out), background var(--d-fast) var(--ease-out);
}

.preset-card:hover {
  border-color: var(--gold-line);
  background: var(--panel);
}

.preset-icon {
  flex: none;
  color: var(--gold);
}

.preset-info {
  min-width: 0;
}

.preset-info h4 {
  font-size: 12.5px;
  font-weight: 500;
  color: var(--text);
}

.preset-info p {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-top: 3px;
  font-size: 11px;
  line-height: 1.6;
  color: var(--t3);
}

.step-count {
  flex: none;
  margin-left: auto;
  font-family: var(--font-mono);
  font-size: 9.5px;
  color: var(--t3);
}

.chain-name {
  font-size: var(--fs-body);
  font-weight: 500;
}

.status-dot {
  flex: none;
  width: 6px;
  height: 6px;
  margin-top: 6px;
  border-radius: 50%;
  background: var(--t3);
}

.status-dot.active {
  background: var(--success);
}

.chain-desc {
  font-size: var(--fs-micro);
  line-height: 1.7;
  color: var(--t2);
}

.chain-steps {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.step-badge {
  padding: 2px 7px;
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  font-family: var(--font-mono);
  font-size: 9.5px;
  color: var(--t3);
}

.execute-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 28px;
  padding: 0 12px;
  border: 1px solid var(--gold-line);
  border-radius: var(--r-sm);
  font-size: var(--fs-micro);
  color: var(--gold);
  transition: background var(--d-fast) var(--ease-out);
}

.execute-btn:hover:not(:disabled) {
  background: var(--gold-soft);
}

.execute-btn:disabled {
  border-color: var(--line);
  color: var(--t3);
  cursor: not-allowed;
}

/* ---- 空态 ---- */
.empty-state {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 56px 16px;
  text-align: center;
  border: 1px dashed var(--line);
  border-radius: var(--r-md);
  color: var(--t3);
}

.empty-state.small {
  padding: 32px 16px;
}

.empty-icon {
  color: var(--line-strong);
}

.empty-state h3 {
  font-family: var(--font-display);
  font-size: var(--fs-body);
  font-weight: 500;
  color: var(--t2);
}

.empty-state p {
  font-size: var(--fs-micro);
  line-height: 1.7;
}

/* ---- 弹窗 ---- */
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 60;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: var(--overlay);
  backdrop-filter: blur(2px);
}

.modal {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 520px;
  max-height: 86vh;
  border: 1px solid var(--line-strong);
  border-radius: var(--r-lg);
  background: var(--panel);
  overflow: hidden;
}

.modal-large {
  max-width: 720px;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 18px;
  border-bottom: 1px solid var(--line);
}

.modal-header h3 {
  font-family: var(--font-display);
  font-size: var(--fs-title-3);
  font-weight: 600;
}

.close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: var(--r-sm);
  color: var(--t3);
}

.close-btn:hover {
  color: var(--text);
  background: var(--panel-2);
}

.modal-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 18px;
  overflow-y: auto;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 18px;
  border-top: 1px solid var(--line);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.05em;
  color: var(--t3);
}

.form-group input[type='text'],
.form-group input[type='number'],
.form-group textarea,
.form-group select {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-body);
  font-size: var(--fs-micro);
  outline: none;
  transition: border-color var(--d-fast) var(--ease-out);
}

.form-group input:focus,
.form-group textarea:focus,
.form-group select:focus {
  border-color: var(--gold-line);
}

.form-group textarea {
  line-height: 1.7;
  resize: vertical;
}

.traffic-slider {
  display: flex;
  align-items: center;
  gap: 12px;
}

.traffic-slider input[type='range'] {
  flex: 1;
  accent-color: var(--gold);
}

.traffic-slider span {
  font-family: var(--font-mono);
  font-size: 10.5px;
  color: var(--t2);
}

.btn-cancel,
.btn-confirm {
  height: 30px;
  padding: 0 14px;
  border-radius: var(--r-sm);
  font-size: var(--fs-micro);
}

.btn-cancel {
  border: 1px solid var(--line-strong);
  color: var(--t2);
}

.btn-cancel:hover {
  color: var(--text);
}

.btn-confirm {
  background: var(--gold);
  color: var(--gold-ink);
  font-weight: 500;
}

.btn-confirm:hover:not(:disabled) {
  background: var(--gold-deep);
}

.btn-confirm:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.preset-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.preset-option {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  cursor: pointer;
  transition: border-color var(--d-fast) var(--ease-out), background var(--d-fast) var(--ease-out);
}

.preset-option:hover {
  border-color: var(--gold-line);
  background: var(--panel-2);
}

.preset-option-icon {
  flex: none;
  color: var(--gold);
}

.preset-option-info h4 {
  font-size: var(--fs-micro);
  font-weight: 500;
}

.preset-option-info p {
  margin-top: 2px;
  font-size: 10.5px;
  color: var(--t3);
}

.execute-result {
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  background: var(--bg);
}

.execute-result h4 {
  margin-bottom: 6px;
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.05em;
  color: var(--t3);
}

.execute-result pre {
  max-height: 240px;
  margin: 0;
  overflow: auto;
  font-family: var(--font-mono);
  font-size: 10px;
  line-height: 1.7;
  color: var(--t2);
  white-space: pre-wrap;
  word-break: break-word;
}

/* ---- 示例详情 ---- */
.example-detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.example-detail-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.example-detail-section h5 {
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.05em;
  color: var(--t3);
}

.example-detail-content {
  max-height: 200px;
  margin: 0;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  background: var(--bg);
  overflow: auto;
  font-family: var(--font-mono);
  font-size: 10.5px;
  line-height: 1.7;
  color: var(--t2);
  white-space: pre-wrap;
  word-break: break-word;
}

.example-detail-meta {
  font-family: var(--font-mono);
  font-size: 9.5px;
  color: var(--t3);
}

/* ---- 思维链详情 ---- */
.cot-detail {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.cot-detail-title {
  font-family: var(--font-display);
  font-size: var(--fs-title-3);
  font-weight: 600;
}

.cot-detail-desc {
  font-size: var(--fs-micro);
  line-height: 1.7;
  color: var(--t2);
}

.cot-detail-section h5 {
  margin-bottom: 6px;
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.05em;
  color: var(--t3);
}

.cot-full-template {
  max-height: 280px;
  margin: 0;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  background: var(--bg);
  overflow: auto;
  font-family: var(--font-mono);
  font-size: 10px;
  line-height: 1.7;
  color: var(--t2);
  white-space: pre-wrap;
  word-break: break-word;
}

.cot-scenarios {
  padding-left: 18px;
  font-size: var(--fs-micro);
  line-height: 1.8;
  color: var(--t2);
  list-style: disc;
}

/* ---- 实验统计 ---- */
.stats-overview {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stats-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.stats-header h4 {
  font-family: var(--font-display);
  font-size: var(--fs-body);
  font-weight: 600;
}

.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.stats-card {
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  text-align: center;
}

.stats-card.version-a {
  border-left: 2px solid var(--steel);
}

.stats-card.version-b {
  border-left: 2px solid var(--gold);
}

.stats-card h5 {
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.05em;
  color: var(--t3);
}

.stats-number {
  margin: 6px 0 2px;
  font-family: var(--font-mono);
  font-size: 26px;
  line-height: 1.1;
  color: var(--text);
}

.stats-label {
  font-size: 10px;
  color: var(--t3);
}

.stats-detail {
  margin-top: 6px;
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--t2);
}

.total-samples {
  font-family: var(--font-mono);
  font-size: 10.5px;
  text-align: center;
  color: var(--t3);
}

@media (max-width: 1024px) {
  .prompt-lab-page {
    padding: 28px 24px 64px;
  }

  .examples-grid,
  .experiments-grid,
  .chains-grid,
  .cot-grid {
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  }
}

@media (max-width: 767px) {
  .prompt-lab-page {
    padding: 24px 16px 56px;
  }

  .lab__bar {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .section-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .section-actions {
    width: 100%;
    flex-wrap: wrap;
  }

  .section-actions :deep(.select-field) {
    flex: 1;
    width: auto;
  }

  .examples-grid,
  .experiments-grid,
  .chains-grid,
  .cot-grid,
  .presets-grid,
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .modal {
    max-height: 92vh;
  }

  .modal-body {
    padding: 14px;
  }
}
</style>
