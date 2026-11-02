import type { Meta, StoryObj } from '@storybook/react';
import type { MappingStoryCase } from './mappingStory.types';
import { createMappingCaseStory, type MappingGroupStoryArgs } from './createMappingCaseStory';
import { hostsFallbackAfterLocalUnmapCase } from './fixtures/cases/hosts_fallback.constants';
import {
  hostComponentNotCreatedCase,
  hostMmOffAddCase,
  hostMmOnDisabledCase,
  hostsModeToggleMappedComponentCase,
  hostTagConstraintErrorCase,
} from './fixtures/cases/hosts_mode.constants';
import { hostsModeOverviewCase } from './fixtures/cases/hosts_mode_overview.constants';

export const clusterHostsCaseIds = [
  'overview',
  'toggle_mapped_component',
  'host.mm_off_add',
  'host.mm_on_disabled',
  'host.component_not_created',
  'host.tag_constraint_error',
  'fallback.after_local_unmap',
] as const;

type CaseId = (typeof clusterHostsCaseIds)[number];
type StoryArgs = MappingGroupStoryArgs<CaseId>;

const cases = {
  overview: hostsModeOverviewCase,
  toggle_mapped_component: hostsModeToggleMappedComponentCase,
  'host.mm_off_add': hostMmOffAddCase,
  'host.mm_on_disabled': hostMmOnDisabledCase,
  'host.component_not_created': hostComponentNotCreatedCase,
  'host.tag_constraint_error': hostTagConstraintErrorCase,
  'fallback.after_local_unmap': hostsFallbackAfterLocalUnmapCase,
} satisfies Record<CaseId, MappingStoryCase>;

const meta = {
  title: 'pages/ClusterMapping/Cluster · Hosts',
  excludeStories: /.*CaseIds$/,
  argTypes: {
    caseId: {
      control: { type: 'select' },
      options: clusterHostsCaseIds,
    },
  },
  args: {
    caseId: 'overview',
  },
} satisfies Meta<StoryArgs>;

export default meta;

export const Cases: StoryObj<StoryArgs> = createMappingCaseStory({ cases });
