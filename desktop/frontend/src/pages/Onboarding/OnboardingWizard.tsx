import { useState } from 'react'
import { StepChooseProvider } from './StepChooseProvider'
import { StepMaterialProviders } from './StepMaterialProviders'
import { StepSummary } from './StepSummary'
import { StepVoiceSelection } from './StepVoiceSelection'

const STEP_COUNT = 4

interface OnboardingWizardProps {
  onFinished: () => void
}

export function OnboardingWizard({ onFinished }: OnboardingWizardProps) {
  const [step, setStep] = useState(0)

  return (
    <div className="mx-auto flex min-h-full max-w-lg flex-col items-center justify-center gap-8 p-8">
      <div className="flex gap-2" aria-label={`Paso ${step + 1} de ${STEP_COUNT}`}>
        {Array.from({ length: STEP_COUNT }, (_, index) => (
          <span
            key={index}
            className={`h-1.5 w-8 rounded-full ${
              index <= step ? 'bg-[var(--color-primary)]' : 'bg-[var(--color-border)]'
            }`}
          />
        ))}
      </div>

      {step === 0 && <StepChooseProvider onNext={() => setStep(1)} />}
      {step === 1 && <StepMaterialProviders onNext={() => setStep(2)} />}
      {step === 2 && <StepVoiceSelection onNext={() => setStep(3)} />}
      {step === 3 && <StepSummary onFinished={onFinished} />}
    </div>
  )
}
