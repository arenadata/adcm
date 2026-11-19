import type { AdcmExecutionPlanGroupKind, AdcmExecutionPlanJobKind, AdcmJobStatus } from '@models/adcm';

export type ExecutionGraphEntityKind = AdcmExecutionPlanJobKind | AdcmExecutionPlanGroupKind;

export type ExecutionGraphNodeData = {
  entityKind: ExecutionGraphEntityKind;
  entityKey: string;
  title: string;
  status: AdcmJobStatus;
  duration: number | null;
  isTerminatable: boolean;
  hasChildren: boolean;
  isExpanded: boolean;
};

export type ExecutionGraphEdgeData = Record<string, never>;
