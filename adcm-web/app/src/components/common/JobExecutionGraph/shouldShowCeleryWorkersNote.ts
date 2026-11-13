import type { AdcmTaskExecutionPlan } from '@models/adcm';
import { walkExecutionPlan } from './executionPlanUtils';

export const shouldShowCeleryWorkersNote = (plan: AdcmTaskExecutionPlan | null): boolean => {
  if (!plan) {
    return false;
  }

  let hasGroup = false;
  let hasParallel = false;

  walkExecutionPlan(plan.children, (node) => {
    if (node.kind === 'job') {
      return;
    }

    hasGroup = true;
    if (node.kind === 'parallel') {
      hasParallel = true;
    }
  });

  return hasGroup && !hasParallel;
};
