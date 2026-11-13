import { AdcmWizardStepStates, AdcmWizardStepType, type AdcmActionWizardProcess } from '@models/adcm/wizard';
import {
  isWizardProcessOnFirstStep,
  resolveProcessOnWizardOpen,
  shouldShowContinueProcessModal,
} from './wizardProcessUtils';

const buildStep = ({
  id,
  state = AdcmWizardStepStates.Created,
}: {
  id: number;
  state?: AdcmWizardStepStates;
}): AdcmActionWizardProcess['stages'][number]['steps'][number] =>
  ({
    id,
    displayName: `Step ${id}`,
    type: AdcmWizardStepType.Configuration,
    state,
    description: '',
    required: false,
    processSyncKey: 'sync',
    configuration: {
      configSchema: {},
      adcmMeta: {},
      config: {},
    },
  }) as AdcmActionWizardProcess['stages'][number]['steps'][number];

const buildProcess = ({
  id = 10,
  currentStep,
  stages,
}: {
  id?: number;
  currentStep: number;
  stages?: AdcmActionWizardProcess['stages'];
}): AdcmActionWizardProcess => ({
  id,
  state: 'created',
  createdAt: '2026-01-01',
  syncKey: 'sync',
  currentStep,
  stages: stages ?? [
    {
      displayName: 'Stage 1',
      description: '',
      steps: [buildStep({ id: 1 }), buildStep({ id: 2 })],
    },
  ],
});

describe('wizardProcessUtils', () => {
  describe('isWizardProcessOnFirstStep', () => {
    test('returns true when currentStep is first step', () => {
      expect(isWizardProcessOnFirstStep(buildProcess({ currentStep: 1 }))).toBe(true);
    });

    test('returns false when currentStep is past first step', () => {
      expect(isWizardProcessOnFirstStep(buildProcess({ currentStep: 2 }))).toBe(false);
    });

    test('returns false when first step is missing', () => {
      expect(isWizardProcessOnFirstStep(buildProcess({ currentStep: 1, stages: [] }))).toBe(false);
    });
  });

  describe('shouldShowContinueProcessModal', () => {
    test('returns true when past first step', () => {
      expect(shouldShowContinueProcessModal(buildProcess({ currentStep: 2 }))).toBe(true);
    });

    test('returns false when on first step', () => {
      expect(shouldShowContinueProcessModal(buildProcess({ currentStep: 1 }))).toBe(false);
    });

    test('returns false when first step is missing', () => {
      expect(shouldShowContinueProcessModal(buildProcess({ currentStep: 2, stages: [] }))).toBe(false);
    });
  });

  describe('resolveProcessOnWizardOpen', () => {
    test('creates a new process when first step is untouched', async () => {
      const existing = buildProcess({ id: 10, currentStep: 1 });
      const created = buildProcess({ id: 99, currentStep: 1 });
      const createProcess = jest.fn().mockResolvedValue(created);

      const result = await resolveProcessOnWizardOpen(existing, createProcess);

      expect(createProcess).toHaveBeenCalledTimes(1);
      expect(result).toBe(created);
    });

    test('does not create when first step is running', async () => {
      const existing = buildProcess({
        id: 10,
        currentStep: 1,
        stages: [
          {
            displayName: 'Stage 1',
            description: '',
            steps: [buildStep({ id: 1, state: AdcmWizardStepStates.Running }), buildStep({ id: 2 })],
          },
        ],
      });
      const createProcess = jest.fn();

      const result = await resolveProcessOnWizardOpen(existing, createProcess);

      expect(createProcess).not.toHaveBeenCalled();
      expect(result).toBe(existing);
    });

    test('does not create when first step is broken', async () => {
      const existing = buildProcess({
        id: 10,
        currentStep: 1,
        stages: [
          {
            displayName: 'Stage 1',
            description: '',
            steps: [buildStep({ id: 1, state: AdcmWizardStepStates.Broken }), buildStep({ id: 2 })],
          },
        ],
      });
      const createProcess = jest.fn();

      const result = await resolveProcessOnWizardOpen(existing, createProcess);

      expect(createProcess).not.toHaveBeenCalled();
      expect(result).toBe(existing);
    });

    test('does not create when past first step', async () => {
      const existing = buildProcess({ id: 10, currentStep: 2 });
      const createProcess = jest.fn();

      const result = await resolveProcessOnWizardOpen(existing, createProcess);

      expect(createProcess).not.toHaveBeenCalled();
      expect(result).toBe(existing);
    });

    test('does not create when first step is missing', async () => {
      const existing = buildProcess({ id: 10, currentStep: 1, stages: [] });
      const createProcess = jest.fn();

      const result = await resolveProcessOnWizardOpen(existing, createProcess);

      expect(createProcess).not.toHaveBeenCalled();
      expect(result).toBe(existing);
    });
  });
});
