import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { api } from './api/client'
import { DiagnosticsScreen } from './pages/Diagnostics/DiagnosticsScreen'
import { OnboardingWizard } from './pages/Onboarding/OnboardingWizard'
import { MainApp } from './pages/Main/MainApp'
import { useAppStore } from './state/appStore'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1 } },
})

function AppShell() {
  const screen = useAppStore((state) => state.screen)
  const setScreen = useAppStore((state) => state.setScreen)

  const handleDiagnosticsReady = async () => {
    try {
      const status = await api.onboardingStatus()
      setScreen(status.completed ? 'main' : 'onboarding')
    } catch {
      setScreen('onboarding')
    }
  }

  if (screen === 'diagnostics') {
    return <DiagnosticsScreen onReady={handleDiagnosticsReady} />
  }
  if (screen === 'onboarding') {
    return <OnboardingWizard onFinished={() => setScreen('main')} />
  }
  return <MainApp />
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppShell />
    </QueryClientProvider>
  )
}

export default App
