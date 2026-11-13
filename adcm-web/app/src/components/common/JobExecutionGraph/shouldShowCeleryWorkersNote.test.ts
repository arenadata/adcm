import { AdcmJobStatus, AdcmTaskExecutionEnvironment } from '@models/adcm';
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
  it('hides for null plan or missing environment', () => {
    expect(shouldShowCeleryWorkersNote({ plan: null, executionEnvironment: AdcmTaskExecutionEnvironment.Local })).toBe(
      false,
    );
    expect(shouldShowCeleryWorkersNote({ plan: withParallelPlan })).toBe(false);
    expect(shouldShowCeleryWorkersNote({ plan: withParallelPlan, executionEnvironment: null })).toBe(false);
  });

  it('hides for flat or sequential-only plans even on local', () => {
    expect(
      shouldShowCeleryWorkersNote({
        plan: flatPlan,
        executionEnvironment: AdcmTaskExecutionEnvironment.Local,
      }),
    ).toBe(false);
    expect(
      shouldShowCeleryWorkersNote({
        plan: sequentialOnlyPlan,
        executionEnvironment: AdcmTaskExecutionEnvironment.Local,
      }),
    ).toBe(false);
  });

  it('shows when plan has parallel and environment is local', () => {
    expect(
      shouldShowCeleryWorkersNote({
        plan: withParallelPlan,
        executionEnvironment: AdcmTaskExecutionEnvironment.Local,
      }),
    ).toBe(true);
  });

  it('hides when plan has parallel but environment is celery', () => {
    expect(
      shouldShowCeleryWorkersNote({
        plan: withParallelPlan,
        executionEnvironment: AdcmTaskExecutionEnvironment.Celery,
      }),
    ).toBe(false);
  });
});
