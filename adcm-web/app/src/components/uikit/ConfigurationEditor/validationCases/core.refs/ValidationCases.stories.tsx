import type { Meta, StoryObj } from '@storybook/react';
import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';
import { createValidationGroupStory, type ValidationGroupStoryArgs } from '../createValidationGroupStory';
import {
  defs_ref_simple_datasets,
  defs_ref_simple_description,
  defs_ref_simple_schema,
} from './defs_ref_simple.constants';
import {
  ref_chain_two_hops_datasets,
  ref_chain_two_hops_description,
  ref_chain_two_hops_schema,
} from './ref_chain_two_hops.constants';
import {
  ref_missing_pointer_datasets,
  ref_missing_pointer_description,
  ref_missing_pointer_schema,
} from './ref_missing_pointer.constants';
import {
  ref_with_adjacent_annotations_datasets,
  ref_with_adjacent_annotations_description,
  ref_with_adjacent_annotations_schema,
} from './ref_with_adjacent_annotations.constants';
import {
  ref_with_adjacent_type_conflict_datasets,
  ref_with_adjacent_type_conflict_description,
  ref_with_adjacent_type_conflict_schema,
} from './ref_with_adjacent_type_conflict.constants';
import {
  defs_shared_schema_used_twice_datasets,
  defs_shared_schema_used_twice_description,
  defs_shared_schema_used_twice_schema,
} from './defs_shared_schema_used_twice.constants';
import {
  ref_inside_allOf_datasets,
  ref_inside_allOf_description,
  ref_inside_allOf_schema,
} from './ref_inside_allOf.constants';
import {
  ref_inside_anyOf_datasets,
  ref_inside_anyOf_description,
  ref_inside_anyOf_schema,
} from './ref_inside_anyOf.constants';
import {
  ref_inside_oneOf_datasets,
  ref_inside_oneOf_description,
  ref_inside_oneOf_schema,
} from './ref_inside_oneOf.constants';

export const coreRefsCaseIds = [
  'core.refs.defs_ref_positive_integer',
  'core.refs.ref_chain_two_hops',
  'core.refs.ref_missing_pointer_fails',
  'core.refs.ref_with_adjacent_annotations',
  'core.refs.ref_with_adjacent_type_conflict',
  'core.refs.defs_shared_schema_used_twice',
  'core.refs.ref_inside_allOf',
  'core.refs.ref_inside_anyOf',
  'core.refs.ref_inside_oneOf',
] as const;

type CaseId = (typeof coreRefsCaseIds)[number];

type StoryArgs = ValidationGroupStoryArgs<CaseId>;

const cases = {
  'core.refs.defs_ref_positive_integer': {
    description: defs_ref_simple_description,
    schema: defs_ref_simple_schema,
    datasets: defs_ref_simple_datasets,
  },
  'core.refs.ref_chain_two_hops': {
    description: ref_chain_two_hops_description,
    schema: ref_chain_two_hops_schema,
    datasets: ref_chain_two_hops_datasets,
  },
  'core.refs.ref_missing_pointer_fails': {
    description: ref_missing_pointer_description,
    schema: ref_missing_pointer_schema,
    datasets: ref_missing_pointer_datasets,
  },
  'core.refs.ref_with_adjacent_annotations': {
    description: ref_with_adjacent_annotations_description,
    schema: ref_with_adjacent_annotations_schema,
    datasets: ref_with_adjacent_annotations_datasets,
  },
  'core.refs.ref_with_adjacent_type_conflict': {
    description: ref_with_adjacent_type_conflict_description,
    schema: ref_with_adjacent_type_conflict_schema,
    datasets: ref_with_adjacent_type_conflict_datasets,
  },
  'core.refs.defs_shared_schema_used_twice': {
    description: defs_shared_schema_used_twice_description,
    schema: defs_shared_schema_used_twice_schema,
    datasets: defs_shared_schema_used_twice_datasets,
  },
  'core.refs.ref_inside_allOf': {
    description: ref_inside_allOf_description,
    schema: ref_inside_allOf_schema,
    datasets: ref_inside_allOf_datasets,
  },
  'core.refs.ref_inside_anyOf': {
    description: ref_inside_anyOf_description,
    schema: ref_inside_anyOf_schema,
    datasets: ref_inside_anyOf_datasets,
  },
  'core.refs.ref_inside_oneOf': {
    description: ref_inside_oneOf_description,
    schema: ref_inside_oneOf_schema,
    datasets: ref_inside_oneOf_datasets,
  },
} satisfies Record<
  CaseId,
  { description: string; schema: ConfigurationSchema; datasets: Record<string, ConfigurationData> }
>;

const meta = {
  title: 'uikit/ConfigurationEditor/ValidationCases/Core $ref + $defs',
  excludeStories: /.*CaseIds$/,
  argTypes: {
    caseId: {
      control: { type: 'select' },
      options: coreRefsCaseIds,
    },
  },
  args: {
    caseId: coreRefsCaseIds[0],
  },
} satisfies Meta<StoryArgs>;

export default meta;
type Story = StoryObj<StoryArgs>;

export const CoreRefs = createValidationGroupStory({ cases }) satisfies Story;
