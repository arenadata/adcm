import { AdcmWizardStepStates, type AdcmActionWizardProcess } from '@models/adcm/wizard';

const getFirstStep = (process: AdcmActionWizardProcess) => {
  return process.stages?.[0]?.steps?.[0];
};

export const isWizardProcessOnFirstStep = (process: AdcmActionWizardProcess): boolean => {
  const firstStep = getFirstStep(process);
  if (firstStep == null) {
    return false;
  }

  return process.currentStep === firstStep.id;
};

export const shouldShowContinueProcessModal = (process: AdcmActionWizardProcess): boolean => {
  const firstStep = getFirstStep(process);
  if (firstStep == null) {
    return false;
  }

  return process.currentStep !== firstStep.id;
};

const shouldAutoRestartWizardProcess = (process: AdcmActionWizardProcess): boolean => {
  const firstStep = getFirstStep(process);
  if (firstStep == null || process.currentStep !== firstStep.id) {
    return false;
  }

  return firstStep.state === AdcmWizardStepStates.Created;
};

export const resolveProcessOnWizardOpen = async (
  process: AdcmActionWizardProcess,
  createProcess: () => Promise<AdcmActionWizardProcess>,
): Promise<AdcmActionWizardProcess> => {
  if (shouldAutoRestartWizardProcess(process)) {
    return createProcess();
  }

  return process;
};
