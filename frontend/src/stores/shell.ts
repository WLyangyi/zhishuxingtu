import { ref, type Component } from 'vue'

export interface TopBarAction {
  id: string
  label: string
  icon?: Component
  variant?: 'primary' | 'secondary' | 'ghost'
  run: () => void
}

const actions = ref<TopBarAction[]>([])

export function useShellStore() {
  return {
    actions,
    setActions(next: TopBarAction[]) {
      actions.value = next
    },
    clearActions() {
      actions.value = []
    }
  }
}
