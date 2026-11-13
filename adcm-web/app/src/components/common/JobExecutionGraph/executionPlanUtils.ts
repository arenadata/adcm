import type { AdcmExecutionPlanNode } from '@models/adcm';

export const walkExecutionPlan = (
  nodes: AdcmExecutionPlanNode[],
  visit: (node: AdcmExecutionPlanNode) => void,
): void => {
  nodes.forEach((node) => {
    visit(node);
    if (node.kind !== 'job') {
      walkExecutionPlan(node.children, visit);
    }
  });
};
