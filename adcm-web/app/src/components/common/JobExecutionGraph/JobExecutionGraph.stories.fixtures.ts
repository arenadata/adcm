import { AdcmJobStatus } from '@models/adcm';
import type { AdcmExecutionPlanJobNode, AdcmTaskExecutionPlan } from '@models/adcm';

const job = (
  id: number,
  name: string,
  displayName: string,
  status: AdcmJobStatus,
  duration: number | null = null,
): AdcmExecutionPlanJobNode => ({
  kind: 'job',
  id,
  name,
  displayName,
  status,
  startTime: null,
  endTime: null,
  duration,
  isTerminatable: true,
});

export const flatPlan: AdcmTaskExecutionPlan = {
  version: 1,
  children: [
    job(1, 'pre_check', 'Pre-check', AdcmJobStatus.Success, 5),
    job(2, 'install', 'Install', AdcmJobStatus.Running, 12),
    job(3, 'finalize', 'Finalize', AdcmJobStatus.Created),
  ],
};

export const baculaLikePlan: AdcmTaskExecutionPlan = {
  version: 1,
  children: [
    job(100, 'bacula_root', 'Bacula', AdcmJobStatus.Running, 7),
    {
      kind: 'parallel',
      name: 'install_pg',
      displayName: 'Install postgresql',
      status: AdcmJobStatus.Success,
      startTime: null,
      endTime: null,
      duration: 40,
      isTerminatable: true,
      children: [
        job(101, 'install_1', 'Install 1', AdcmJobStatus.Success, 26),
        job(102, 'install_2', 'Install 2', AdcmJobStatus.Success, 26),
        job(103, 'install_3', 'Install 3', AdcmJobStatus.Success, 26),
      ],
    },
    job(104, 'install_director', 'Install Director', AdcmJobStatus.Success, 8),
    {
      kind: 'parallel',
      name: 'bacula_stages',
      displayName: 'Bacula',
      status: AdcmJobStatus.Running,
      startTime: null,
      endTime: null,
      duration: null,
      isTerminatable: true,
      children: [
        job(201, 'stage_11', 'Stage 1 1', AdcmJobStatus.Success, 5),
        {
          kind: 'parallel',
          name: 'stage_12',
          displayName: 'Stage 1 2',
          status: AdcmJobStatus.Success,
          startTime: null,
          endTime: null,
          duration: 20,
          isTerminatable: true,
          children: [
            job(211, 'stage_121', 'Stage 1 2 1', AdcmJobStatus.Success, 10),
            job(212, 'stage_122', 'Stage 1 2 2', AdcmJobStatus.Success, 12),
            job(213, 'stage_123', 'Stage 1 2 3', AdcmJobStatus.Success, 9),
          ],
        },
        job(220, 'stage_2', 'Stage 2', AdcmJobStatus.Failed, 3),
        job(230, 'stage_3', 'Stage 3', AdcmJobStatus.Running, 4),
      ],
    },
    job(300, 'init', 'Init', AdcmJobStatus.Created),
    job(301, 'final', 'Final and send messages error', AdcmJobStatus.Created),
  ],
};

export const advanceBaculaStatuses = (plan: AdcmTaskExecutionPlan): AdcmTaskExecutionPlan => {
  const nextStatus = (status: AdcmJobStatus): AdcmJobStatus => {
    if (status === AdcmJobStatus.Created) return AdcmJobStatus.Running;
    if (status === AdcmJobStatus.Running) return AdcmJobStatus.Success;
    return status;
  };

  const mapNode = (node: AdcmTaskExecutionPlan['children'][number]): typeof node => {
    if (node.kind === 'job') {
      return { ...node, status: nextStatus(node.status) };
    }

    const children = node.children.map(mapNode);
    return { ...node, children, status: nextStatus(node.status) };
  };

  return {
    ...plan,
    children: plan.children.map(mapNode),
  };
};
