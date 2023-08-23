import { Meta, StoryObj } from '@storybook/react';
import WizardSteps from '@uikit/WizardSteps/WizardSteps';
import { useState } from 'react';

type Story = StoryObj<typeof WizardSteps>;
export default {
  title: 'uikit/WizardSteps',
  component: WizardSteps,
} as Meta<typeof WizardSteps>;

const steps = [
  { title: 'First', key: 'first' },
  { title: 'Second', key: 'second' },
  { title: 'Third', key: 'third' },
];

const WizardStepsExample = () => {
  const [currentStep, setCurrentStep] = useState(steps[0].key);
  return <WizardSteps steps={steps} currentStep={currentStep} onChangeStep={setCurrentStep} />;
};

export const TextElement: Story = {
  render: () => {
    return <WizardStepsExample />;
  },
};
