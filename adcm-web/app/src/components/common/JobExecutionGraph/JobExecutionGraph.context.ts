import type { Context } from 'react';
import { createContextHelper, useContextHelper } from '@hooks/useContextHelper';
import type { ExecutionGraphNodeData } from './types';

export type JobExecutionGraphNodeActionType = 'skip' | 'stop';

export type JobExecutionGraphNodeActionPayload = {
  nodeId: string;
  data: ExecutionGraphNodeData;
  action: JobExecutionGraphNodeActionType;
};

export type JobExecutionGraphContextOptions = {
  onNodeAction?: (payload: JobExecutionGraphNodeActionPayload) => void;
  onToggleExpand?: (nodeId: string) => void;
};

export const JobExecutionGraphContext =
  createContextHelper<JobExecutionGraphContextOptions>('JobExecutionGraphContext');

export const useJobExecutionGraphContext = (): JobExecutionGraphContextOptions =>
  useContextHelper<JobExecutionGraphContextOptions>(
    JobExecutionGraphContext as Context<JobExecutionGraphContextOptions | undefined>,
  );
