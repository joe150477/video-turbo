import { create } from 'zustand'

export type Screen = 'diagnostics' | 'onboarding' | 'main'

interface AppState {
  screen: Screen
  setScreen: (screen: Screen) => void
}

export const useAppStore = create<AppState>((set) => ({
  screen: 'diagnostics',
  setScreen: (screen) => set({ screen }),
}))
