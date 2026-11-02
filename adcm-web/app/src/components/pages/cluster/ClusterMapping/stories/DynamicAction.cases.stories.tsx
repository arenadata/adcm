import type { Meta, StoryObj } from '@storybook/react';
import type { MappingStoryCase } from './mappingStory.types';
import { createMappingCaseStory, type MappingGroupStoryArgs } from './createMappingCaseStory';
import {
  actionEmptyNoServicesCase,
  actionFlatEditableFirstCase,
  actionMmBlockAddCase,
  actionRulesAddOnlyBaselineCase,
  actionRulesAddRemoveCase,
} from './fixtures/cases/action.catalog.constants';

export const dynamicActionCaseIds = [
  'flat.editable_first',
  'rules.add_only_baseline',
  'rules.add_remove',
  'empty.no_services',
  'mm.block_add',
] as const;

type CaseId = (typeof dynamicActionCaseIds)[number];
type StoryArgs = MappingGroupStoryArgs<CaseId>;

const cases = {
  'flat.editable_first': actionFlatEditableFirstCase,
  'rules.add_only_baseline': actionRulesAddOnlyBaselineCase,
  'rules.add_remove': actionRulesAddRemoveCase,
  'empty.no_services': actionEmptyNoServicesCase,
  'mm.block_add': actionMmBlockAddCase,
} satisfies Record<CaseId, MappingStoryCase>;

const meta = {
  title: 'pages/ClusterMapping/Dynamic Action',
  excludeStories: /.*CaseIds$/,
  argTypes: {
    caseId: {
      control: { type: 'select' },
      options: dynamicActionCaseIds,
    },
  },
  args: {
    caseId: 'flat.editable_first',
  },
} satisfies Meta<StoryArgs>;

export default meta;

export const Cases: StoryObj<StoryArgs> = createMappingCaseStory({ cases });
