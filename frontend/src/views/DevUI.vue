<template>
  <div class="dev-ui atlas-grid">
    <div class="dev-ui__inner">
      <PageHeader
        kicker="DESIGN SYSTEM · P1"
        title="精密星图组件库"
        description="28 个基础组件与 6 个领域组件的可交互预览。四态、双主题、键盘行为都在这里验收。"
      >
        <template #actions>
          <SegmentedControl
            :model-value="themeMode"
            :items="themeItems"
            aria-label="主题切换"
            @update:model-value="onThemeChange"
          />
          <AppButton variant="secondary" size="sm" @click="paletteOpen = true">
            打开命令面板
            <template #icon><Command :size="14" /></template>
          </AppButton>
        </template>
      </PageHeader>

      <!-- 01 按钮 -->
      <section id="buttons" class="demo">
        <span class="readout">01 / BUTTONS</span>
        <div class="demo__row">
          <AppButton>主按钮</AppButton>
          <AppButton variant="secondary">次按钮</AppButton>
          <AppButton variant="ghost">幽灵</AppButton>
          <AppButton variant="danger">危险</AppButton>
          <AppButton variant="link">文本链接</AppButton>
        </div>
        <div class="demo__row">
          <AppButton size="sm">小号</AppButton>
          <AppButton size="md">中号</AppButton>
          <AppButton size="lg">大号</AppButton>
          <AppButton loading>保存中</AppButton>
          <AppButton disabled>已禁用</AppButton>
          <IconButton label="设置"><Settings :size="16" /></IconButton>
          <IconButton label="收藏" active><Star :size="16" /></IconButton>
        </div>
      </section>

      <!-- 02 表单 -->
      <section id="form" class="demo">
        <span class="readout">02 / FORM</span>
        <div class="demo__grid">
          <AppInput v-model="form.title" label="标题" placeholder="给笔记起个名字" hint="支持 Markdown" />
          <AppInput v-model="form.bad" label="错误态" invalid error="标题不能为空" />
          <AppInput :model-value="'只读字段'" label="禁用态" disabled />
          <AppSelect v-model="form.scope" label="归属" :options="scopeOptions" />
          <AppSelect :model-value="'work'" label="禁用下拉" :options="scopeOptions" disabled />
          <AppSwitch v-model="form.publish" label="保存后立即发布" />
          <AppSwitch :model-value="true" label="禁用开关" disabled />
          <SearchInput v-model="form.search" placeholder="搜索笔记…" />
        </div>
        <AppTextarea v-model="form.summary" label="摘要" :maxlength="120" show-count :rows="3" />
      </section>

      <!-- 03 标记与状态 -->
      <section id="marks" class="demo">
        <span class="readout">03 / MARKS</span>
        <div class="demo__row">
          <Badge tone="gold">笔记</Badge>
          <Badge tone="steel">标签</Badge>
          <Badge tone="sage">素材</Badge>
          <Badge tone="danger" dot>失败</Badge>
          <Badge tone="success" dot>已连接</Badge>
          <AppTag tone="gold" closable @close="notify('移除标签')">Agentic RAG</AppTag>
          <AppTag tone="steel">双链</AppTag>
        </div>
        <div class="demo__row">
          <span class="demo__inline"><StatusDot status="running" label="运行中" /> 运行中</span>
          <span class="demo__inline"><StatusDot status="success" label="成功" /> 成功</span>
          <span class="demo__inline"><StatusDot status="error" label="失败" /> 失败</span>
          <span class="demo__inline"><StatusDot status="idle" label="空闲" /> 空闲</span>
          <AppAvatar name="流离" size="sm" />
          <AppAvatar name="流离" size="md" />
          <AppAvatar name="ZS" size="lg" />
          <Kbd keys="⌘ K" />
          <Kbd keys="Esc" />
        </div>
      </section>

      <!-- 04 容器 -->
      <section id="containers" class="demo">
        <span class="readout">04 / CONTAINERS</span>
        <div class="demo__grid demo__grid--two">
          <AppCard title="观测记录" description="E1 面板：发丝描边，无阴影" interactive>
            <p class="demo__text">笔记是恒星，链接是星座。卡片只用于真正需要边界的内容。</p>
          </AppCard>
          <FlatPanel title="最近编辑" kicker="INDEX">
            <ul class="demo__list">
              <li><span>Agentic RAG 设计笔记</span><span class="num">21:34</span></li>
              <li><span>知识图谱布局复盘</span><span class="num">20:12</span></li>
              <li><span>向量检索实验记录</span><span class="num">18:07</span></li>
            </ul>
          </FlatPanel>
        </div>
        <div class="demo__row">
          <AppButton variant="secondary" size="sm" @click="modalOpen = true">打开弹窗</AppButton>
          <AppButton variant="secondary" size="sm" @click="drawerOpen = true">打开抽屉</AppButton>
        </div>
      </section>

      <!-- 05 导航与切换 -->
      <section id="navigation" class="demo">
        <span class="readout">05 / NAVIGATION</span>
        <Breadcrumb :items="[{ label: '我的笔记', to: '/library' }, { label: '工作' }, { label: 'Agentic RAG 设计笔记' }]" />
        <AppTabs v-model="tab" :items="tabItems">
          <template #default="{ active }">
            <p class="demo__text">当前分组：{{ active }}。标签页使用 Reka UI，方向键可切换。</p>
          </template>
        </AppTabs>
        <div class="demo__row">
          <SegmentedControl v-model="viewMode" :items="viewItems" />
          <span class="demo__text">当前视图：{{ viewMode }}</span>
        </div>
        <ContextMenu :items="contextItems" @select="notify(`上下文操作：${$event}`)">
          <div class="demo__context">在此区域右键，打开上下文菜单</div>
        </ContextMenu>
      </section>

      <!-- 06 反馈 -->
      <section id="feedback" class="demo">
        <span class="readout">06 / FEEDBACK</span>
        <div class="demo__row">
          <AppButton size="sm" @click="toast.success('已保存', '笔记已写入知识库')">成功 Toast</AppButton>
          <AppButton size="sm" variant="danger" @click="toast.error('保存失败', '网络连接中断，请重试')">
            错误 Toast
          </AppButton>
          <AppTooltip content="新建笔记" shortcut="⌘ N">
            <AppButton variant="secondary" size="sm">悬停看 Tooltip</AppButton>
          </AppTooltip>
          <Spinner :size="18" />
        </div>
        <div class="demo__grid demo__grid--two">
          <div class="demo__box">
            <Skeleton :lines="3" />
          </div>
          <div class="demo__box">
            <EmptyState title="这里还没有笔记" description="写下第一条，或让 AI 帮你整理。">
              <AppButton size="sm">新建笔记</AppButton>
            </EmptyState>
          </div>
        </div>
      </section>

      <!-- 07 领域组件 -->
      <section id="domain" class="demo">
        <span class="readout">07 / DOMAIN</span>

        <div class="demo-hero">
          <StarField :density="60" />
          <div class="demo-hero__content">
            <span class="readout readout--gold">OBSERVATORY</span>
            <h3 class="demo-hero__title">三层视差星场 + 星座描绘</h3>
            <ConstellationArt variant="hero" :width="360" :height="200" />
          </div>
        </div>

        <div class="demo__grid demo__grid--three">
          <MetricCard label="NOTES" :value="128" :trend="12" trend-label="较上周" />
          <MetricCard label="WORDS" :value="182340" unit="字" note="全部笔记正文" />
          <MetricCard label="TRACES" :value="96" :trend="-4" trend-label="较昨日" />
        </div>

        <div class="demo__messages">
          <MessageBubble role="user" time="23:04">
            帮我把今天的实验记录整理成一篇笔记。
          </MessageBubble>
          <MessageBubble role="assistant" name="观测员" time="23:04" streaming>
            已检索到 3 条相关记录，正在按"实验目的 / 过程 / 结论"整理。
          </MessageBubble>
          <MessageBubble role="system" time="23:05">APPROVAL REQUIRED · WRITE_NOTE</MessageBubble>
        </div>

        <div class="demo__approvals">
          <ApprovalCard
            title="写入笔记：Agentic RAG 实验记录"
            summary="将整理后的 1,240 字写入知识库，归属「工作 / 实验」"
            :payload="JSON.stringify({ title: 'Agentic RAG 实验记录', folder: '工作/实验', words: 1240 }, null, 2)"
            :status="approvalStatus"
            :decided-at="approvalTime"
            @approve="decide('approved')"
            @reject="decide('rejected')"
          />
          <ApprovalCard title="写入笔记：复盘" status="approved" decided-at="22:41" />
          <ApprovalCard title="写入笔记：废弃草稿" status="rejected" decided-at="21:18" />
        </div>

        <CodeBlock
          language="PROMPT"
          code="你是一名观测员。请基于 {{context}} 回答 {{question}}，并标注引用来源。"
        />
      </section>
    </div>

    <AppModal v-model:open="modalOpen" title="导入笔记" description="支持 PDF、字幕与网页链接">
      <p class="demo__text">弹窗使用 Reka UI Dialog：焦点陷阱、Esc 关闭、遮罩点击关闭均由原语保证。</p>
      <template #footer>
        <AppButton variant="ghost" size="sm" @click="modalOpen = false">取消</AppButton>
        <AppButton size="sm" @click="modalOpen = false">开始导入</AppButton>
      </template>
    </AppModal>

    <AppDrawer v-model:open="drawerOpen" title="链接与出链" kicker="INSPECTOR">
      <ul class="demo__list">
        <li><span>出链 · Agentic RAG 架构</span><span class="num">12</span></li>
        <li><span>出链 · 向量检索实验</span><span class="num">7</span></li>
        <li><span>入链 · 知识库周报</span><span class="num">3</span></li>
      </ul>
    </AppDrawer>

    <CommandPalette
      v-model:open="paletteOpen"
      :notes="paletteNotes"
      :actions="paletteActions"
      @select="onCommandSelect"
    />

    <AppToast />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Command, Settings, Star } from 'lucide-vue-next'
import PageHeader from '@/components/ui/PageHeader.vue'
import AppButton from '@/components/ui/AppButton.vue'
import IconButton from '@/components/ui/IconButton.vue'
import AppInput from '@/components/ui/AppInput.vue'
import AppTextarea from '@/components/ui/AppTextarea.vue'
import AppSelect from '@/components/ui/AppSelect.vue'
import AppSwitch from '@/components/ui/AppSwitch.vue'
import SearchInput from '@/components/ui/SearchInput.vue'
import Badge from '@/components/ui/Badge.vue'
import AppTag from '@/components/ui/AppTag.vue'
import StatusDot from '@/components/ui/StatusDot.vue'
import AppAvatar from '@/components/ui/AppAvatar.vue'
import Kbd from '@/components/ui/Kbd.vue'
import AppCard from '@/components/ui/AppCard.vue'
import FlatPanel from '@/components/ui/FlatPanel.vue'
import AppModal from '@/components/ui/AppModal.vue'
import AppDrawer from '@/components/ui/AppDrawer.vue'
import AppTabs from '@/components/ui/AppTabs.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import AppToast from '@/components/ui/AppToast.vue'
import AppTooltip from '@/components/ui/AppTooltip.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import Spinner from '@/components/ui/Spinner.vue'
import Breadcrumb from '@/components/ui/Breadcrumb.vue'
import ContextMenu from '@/components/ui/ContextMenu.vue'
import CommandPalette, { type CommandItem } from '@/components/ui/CommandPalette.vue'
import StarField from '@/components/domain/StarField.vue'
import ConstellationArt from '@/components/domain/ConstellationArt.vue'
import MetricCard from '@/components/domain/MetricCard.vue'
import MessageBubble from '@/components/domain/MessageBubble.vue'
import ApprovalCard from '@/components/domain/ApprovalCard.vue'
import CodeBlock from '@/components/domain/CodeBlock.vue'
import { useThemeStore } from '@/stores/theme'
import { useToast } from '@/lib/toast'

const themeStore = useThemeStore()
const toast = useToast()

const themeMode = ref(themeStore.isDark ? 'dark' : 'light')
const themeItems = [
  { label: '暗色', value: 'dark' },
  { label: '浅色', value: 'light' }
]

const form = ref({ title: '', bad: '', scope: 'work', publish: false, search: '', summary: '' })
const scopeOptions = [
  { label: '工作', value: 'work' },
  { label: '个人', value: 'personal' },
  { label: '素材', value: 'assets' }
]

const tab = ref('few')
const tabItems = [
  { label: 'Few-Shot', value: 'few', count: 12 },
  { label: '链', value: 'chain', count: 4 },
  { label: '评估', value: 'eval' }
]

const viewMode = ref('grid')
const viewItems = [
  { label: '网格', value: 'grid' },
  { label: '列表', value: 'list' }
]

const contextItems = [
  { label: '打开笔记', value: 'open', shortcut: '↵' },
  { label: '复制双链', value: 'link', shortcut: '⌘ L' },
  { separator: true, label: '' },
  { label: '删除', value: 'delete', danger: true }
]

const modalOpen = ref(false)
const drawerOpen = ref(false)
const paletteOpen = ref(false)

const approvalStatus = ref<'pending' | 'approved' | 'rejected'>('pending')
const approvalTime = ref('')

const paletteNotes: CommandItem[] = [
  { id: 'n1', label: 'Agentic RAG 设计笔记', hint: '刚刚编辑' },
  { id: 'n2', label: '知识图谱布局复盘', hint: '昨天' },
  { id: 'n3', label: '向量检索实验记录', hint: '2 天前' }
]

const paletteActions: CommandItem[] = [
  { id: 'a1', label: '新建笔记', shortcut: '⌘ N' },
  { id: 'a2', label: '切换主题', shortcut: '⌘ ⇧ L' },
  { id: 'a3', label: '打开导入', shortcut: '⌘ I' }
]

function onThemeChange(value: string) {
  themeMode.value = value
  themeStore.setTheme(value === 'dark')
}

function notify(message: string) {
  toast.info(message)
}

function decide(status: 'approved' | 'rejected') {
  approvalStatus.value = status
  approvalTime.value = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  toast.success(status === 'approved' ? '已批准执行' : '已拒绝执行')
}

function onCommandSelect(item: CommandItem) {
  toast.info(`执行：${item.label}`)
}

onMounted(() => {
  themeMode.value = themeStore.isDark ? 'dark' : 'light'
  if (location.hash) {
    requestAnimationFrame(() => document.querySelector(location.hash)?.scrollIntoView())
  }
})
</script>

<style scoped>
.dev-ui {
  position: relative;
  min-height: 100%;
  background: transparent;
}

.dev-ui__inner {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 36px;
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 40px 32px 80px;
}

.demo {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-bottom: 28px;
  border-bottom: 1px solid var(--line);
}

.demo__row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px 14px;
}

.demo__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}

.demo__grid--two {
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
}

.demo__grid--three {
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}

.demo__inline {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--t2);
}

.demo__text {
  font-size: 13px;
  line-height: 1.7;
  color: var(--t2);
}

.demo__list {
  display: flex;
  flex-direction: column;
}

.demo__list li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 9px 0;
  border-bottom: 1px solid var(--line);
  font-size: 13px;
  color: var(--t2);
}

.demo__list li:last-child {
  border-bottom: 0;
}

.demo__box {
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  padding: 16px;
  min-height: 140px;
}

.demo__context {
  padding: 18px 20px;
  border: 1px dashed var(--line-strong);
  border-radius: var(--r-md);
  font-size: 12px;
  color: var(--t3);
  cursor: context-menu;
}

.demo-hero {
  position: relative;
  display: flex;
  align-items: center;
  min-height: 240px;
  padding: 24px 28px;
  border: 1px solid var(--line);
  border-radius: var(--r-lg);
  background: var(--bg);
  overflow: hidden;
}

.demo-hero__content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.demo-hero__title {
  font-family: var(--font-display);
  font-size: 26px;
  font-weight: 500;
  letter-spacing: -0.03em;
}

.demo__messages {
  display: flex;
  flex-direction: column;
  gap: 18px;
  max-width: 720px;
  padding: 20px;
  border: 1px solid var(--line);
  border-radius: var(--r-lg);
}

.demo__approvals {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 720px;
}

@media (max-width: 767px) {
  .dev-ui__inner {
    padding: 24px 16px 56px;
  }

  .demo__grid,
  .demo__grid--two,
  .demo__grid--three {
    grid-template-columns: 1fr;
  }

  .demo__row {
    gap: 8px 10px;
  }
}
</style>
