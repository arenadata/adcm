import type { Meta, StoryObj } from '@storybook/react';
import type { MappingStoryCase } from './mappingStory.types';
import { createMappingCaseStory, type MappingGroupStoryArgs } from './createMappingCaseStory';
import {
  availabilityCreatedServiceCase,
  availabilityServiceNotCreatedCase,
} from './fixtures/cases/availability_created_vs_installed.constants';
import {
  availabilityMmHostAddCase,
  availabilityMmHostUnmapCase,
} from './fixtures/cases/availability_mm_host.constants';
import {
  clusterComponentsErrorsServiceMarkerCase,
  clusterComponentsLayoutNameAzCase,
} from './fixtures/cases/cluster_components_extra.constants';
import { componentsModeOverviewCase } from './fixtures/cases/components_mode.constants';
import { constraintAllHostsCase } from './fixtures/cases/constraint_all_hosts.constants';
import { constraintExactNCase } from './fixtures/cases/constraint_exact_n.constants';
import { constraintOddCase } from './fixtures/cases/constraint_odd.constants';
import { constraintRangeCase } from './fixtures/cases/constraint_range.constants';
import { dependencyNotAddedCase } from './fixtures/cases/dependency_not_added.constants';
import { dependencyRequiredCase } from './fixtures/cases/dependency_required.constants';
import { optionalZeroHostsCase } from './fixtures/cases/optional_zero_hosts.constants';
import { validMappedCase } from './fixtures/cases/valid_mapped.constants';

export const clusterComponentsCaseIds = [
  'overview',
  'constraint.odd',
  'constraint.exact',
  'constraint.range',
  'constraint.all',
  'optional.zero_ok',
  'valid.mapped',
  'avail.service_not_created',
  'avail.service_created',
  'avail.mm_block_add',
  'avail.mm_keep_unmap',
  'dep.not_added',
  'dep.required',
  'errors.service_marker',
  'layout.name_az',
] as const;

type CaseId = (typeof clusterComponentsCaseIds)[number];
type StoryArgs = MappingGroupStoryArgs<CaseId>;

const cases = {
  overview: componentsModeOverviewCase,
  'constraint.odd': constraintOddCase,
  'constraint.exact': constraintExactNCase,
  'constraint.range': constraintRangeCase,
  'constraint.all': constraintAllHostsCase,
  'optional.zero_ok': optionalZeroHostsCase,
  'valid.mapped': validMappedCase,
  'avail.service_not_created': availabilityServiceNotCreatedCase,
  'avail.service_created': availabilityCreatedServiceCase,
  'avail.mm_block_add': availabilityMmHostAddCase,
  'avail.mm_keep_unmap': availabilityMmHostUnmapCase,
  'dep.not_added': dependencyNotAddedCase,
  'dep.required': dependencyRequiredCase,
  'errors.service_marker': clusterComponentsErrorsServiceMarkerCase,
  'layout.name_az': clusterComponentsLayoutNameAzCase,
} satisfies Record<CaseId, MappingStoryCase>;

const meta = {
  title: 'pages/ClusterMapping/Cluster · Components',
  excludeStories: /.*CaseIds$/,
  argTypes: {
    caseId: {
      control: { type: 'select' },
      options: clusterComponentsCaseIds,
    },
  },
  args: {
    caseId: 'overview',
  },
} satisfies Meta<StoryArgs>;

export default meta;

export const Cases: StoryObj<StoryArgs> = createMappingCaseStory({ cases });
