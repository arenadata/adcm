import type { Meta, StoryObj } from '@storybook/react';
import type { MappingStoryCase } from './mappingStory.types';
import { createMappingCaseStory, type MappingGroupStoryArgs } from './createMappingCaseStory';
import {
  wizardErrorsConstraintMarkerCase,
  wizardHostsModeAddOnlyCase,
  wizardLayoutEditableFirstCase,
  wizardRulesAddOnlyBaselineCase,
  wizardRulesAddRemoveCase,
  wizardRulesNoneOnComponentCase,
  wizardRulesRemoveOnlyCase,
} from './fixtures/cases/wizard.catalog.constants';

export const wizardCaseIds = [
  'rules.add_remove',
  'rules.add_only_baseline',
  'rules.remove_only',
  'rules.none_on_component',
  'layout.editable_first',
  'errors.constraint_marker',
  'hosts_mode.add_only',
] as const;

type CaseId = (typeof wizardCaseIds)[number];
type StoryArgs = MappingGroupStoryArgs<CaseId>;

const cases = {
  'rules.add_remove': wizardRulesAddRemoveCase,
  'rules.add_only_baseline': wizardRulesAddOnlyBaselineCase,
  'rules.remove_only': wizardRulesRemoveOnlyCase,
  'rules.none_on_component': wizardRulesNoneOnComponentCase,
  'layout.editable_first': wizardLayoutEditableFirstCase,
  'errors.constraint_marker': wizardErrorsConstraintMarkerCase,
  'hosts_mode.add_only': wizardHostsModeAddOnlyCase,
} satisfies Record<CaseId, MappingStoryCase>;

const meta = {
  title: 'pages/ClusterMapping/Wizard',
  excludeStories: /.*CaseIds$/,
  argTypes: {
    caseId: {
      control: { type: 'select' },
      options: wizardCaseIds,
    },
  },
  args: {
    caseId: 'rules.add_only_baseline',
  },
} satisfies Meta<StoryArgs>;

export default meta;

export const Cases: StoryObj<StoryArgs> = createMappingCaseStory({ cases });
