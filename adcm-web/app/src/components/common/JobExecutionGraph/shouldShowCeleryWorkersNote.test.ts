import { AdcmJobStatus } from '@models/adcm';
import type { AdcmTaskExecutionPlan } from '@models/adcm';
import { shouldShowCeleryWorkersNote } from './shouldShowCeleryWorkersNote';

const flatPlan: AdcmTaskExecutionPlan = {
  version: 1,
  children: [
    {
      kind: 'job',
      id: 1,
      name: 'a',
      displayName: 'A',
      status: AdcmJobStatus.Success,
      startTime: null,
      endTime: null,
      duration: 1,
      isTerminatable: false,
    },
  ],
};

const sequentialOnlyPlan: AdcmTaskExecutionPlan = {
  version: 1,
  children: [
    {
      kind: 'sequential',
      name: 'seq',
      displayName: 'Seq',
      status: AdcmJobStatus.Success,
      startTime: null,
      endTime: null,
      duration: 1,
      isTerminatable: false,
      children: [
        {
          kind: 'job',
          id: 1,
          name: 'a',
          displayName: 'A',
          status: AdcmJobStatus.Success,
          startTime: null,
          endTime: null,
          duration: 1,
          isTerminatable: false,
        },
      ],
    },
  ],
};

const withParallelPlan: AdcmTaskExecutionPlan = {
  version: 1,
  children: [
    {
      kind: 'parallel',
      name: 'par',
      displayName: 'Par',
      status: AdcmJobStatus.Running,
      startTime: null,
      endTime: null,
      duration: null,
      isTerminatable: true,
      children: [
        {
          kind: 'job',
          id: 1,
          name: 'a',
          displayName: 'A',
          status: AdcmJobStatus.Created,
          startTime: null,
          endTime: null,
          duration: null,
          isTerminatable: true,
        },
      ],
    },
  ],
};

describe('shouldShowCeleryWorkersNote', () => {
  it('hides for null or flat job list', () => {
    expect(shouldShowCeleryWorkersNote(null)).toBe(false);
    expect(shouldShowCeleryWorkersNote(flatPlan)).toBe(false);
  });

  it('shows when plan has nested groups and no parallel', () => {
    expect(shouldShowCeleryWorkersNote(sequentialOnlyPlan)).toBe(true);
  });

  it('hides when plan already has parallel groups', () => {
    expect(shouldShowCeleryWorkersNote(withParallelPlan)).toBe(false);
  });
});
