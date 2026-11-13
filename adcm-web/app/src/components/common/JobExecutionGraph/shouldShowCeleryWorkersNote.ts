import { AdcmTaskExecutionEnvironment, type AdcmTaskExecutionPlan } from '@models/adcm';
import { walkExecutionPlan } from './executionPlanUtils';

type ShouldShowCeleryWorkersNoteArgs = {
  plan: AdcmTaskExecutionPlan | null;
  executionEnvironment?: AdcmTaskExecutionEnvironment | null;
};

export const shouldShowCeleryWorkersNote = ({
  plan,
  executionEnvironment,
}: ShouldShowCeleryWorkersNoteArgs): boolean => {
  if (!plan || executionEnvironment !== AdcmTaskExecutionEnvironment.Local) {
    return false;
  }

  let hasParallel = false;

  walkExecutionPlan(plan.children, (node) => {
    if (node.kind === 'parallel') {
      hasParallel = true;
    }
  });

  return hasParallel;
};
