import { type AdcmActionProcessStep, AdcmWizardStepStates } from '@models/adcm/wizard';
import { type AdcmJob, AdcmJobStatus } from '@models/adcm';

export const isStepFailed = (step: AdcmActionProcessStep, isValid: boolean, jobsData?: AdcmJob): boolean => {
  return !isValid || jobsData?.status === AdcmJobStatus.Failed || step.state === AdcmWizardStepStates.Broken;
};
