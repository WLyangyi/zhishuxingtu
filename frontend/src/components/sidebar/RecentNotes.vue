<template>
  <div class="sidebar-section">
    <div class="section-header">
      <h3>最近内容</h3>
    </div>
    <div class="recent-notes">
      <div
        v-for="note in recentNotes"
        :key="note.id"
        class="note-item"
        tabindex="0"
        role="button"
        @click="openNote(note.id)"
        @keydown.enter="openNote(note.id)"
      >
        <span class="note-dot"></span>
        <span class="note-title-text">{{ note.title }}</span>
      </div>
      <div v-if="notesStore.notes.length === 0" class="empty-hint">
        暂无内容
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useNotesStore } from '@/stores/notes'

const router = useRouter()
const notesStore = useNotesStore()

const recentNotes = computed(() => notesStore.notes.slice(0, 5))

function openNote(noteId: string) {
  router.push(`/notes/${noteId}`)
}
</script>

<style scoped lang="scss">
.sidebar-section {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-subtle);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;

  h3 {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
}

.recent-notes {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.note-item {
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 13px;
  color: var(--text-secondary);
  transition: all var(--transition-fast);
  display: flex;
  align-items: center;
  gap: 8px;

  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);

    .note-dot {
      background: var(--primary-color);
    }
  }

  &:focus {
    outline: none;
    background: var(--bg-active);
  }

  .note-dot {
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: var(--text-muted);
    transition: background var(--transition-fast);
    flex-shrink: 0;
  }

  .note-title-text {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.empty-hint {
  padding: 16px;
  text-align: center;
  color: var(--text-muted);
  font-size: 12px;
}
</style>
