import type { Meta, StoryObj } from '@storybook/react';
import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';
import { createValidationGroupStory, type ValidationGroupStoryArgs } from '../createValidationGroupStory';
import { allOf_basic_datasets, allOf_basic_description, allOf_basic_schema } from './allOf_basic.constants';
import { allOf_conflict_datasets, allOf_conflict_description, allOf_conflict_schema } from './allOf_conflict.constants';
import { anyOf_basic_datasets, anyOf_basic_description, anyOf_basic_schema } from './anyOf_basic.constants';
import {
  anyOf_multiple_valid_datasets,
  anyOf_multiple_valid_description,
  anyOf_multiple_valid_schema,
} from './anyOf_multiple_valid.constants';
import { oneOf_basic_datasets, oneOf_basic_description, oneOf_basic_schema } from './oneOf_basic.constants';
import {
  oneOf_type_variants_datasets,
  oneOf_type_variants_description,
  oneOf_type_variants_schema,
} from './oneOf_type_variants.constants';
import { not_basic_datasets, not_basic_description, not_basic_schema } from './not_basic.constants';
import { not_pattern_datasets, not_pattern_description, not_pattern_schema } from './not_pattern.constants';

export const coreApplicatorsCaseIds = [
  'core.applicators.allOf_basic',
  'core.applicators.allOf_conflict',
  'core.applicators.anyOf_basic',
  'core.applicators.anyOf_multiple_valid',
  'core.applicators.oneOf_basic',
  'core.applicators.oneOf_type_variants',
  'core.applicators.not_basic',
  'core.applicators.not_pattern',
] as const;

type CaseId = (typeof coreApplicatorsCaseIds)[number];

type StoryArgs = ValidationGroupStoryArgs<CaseId>;

const cases = {
  'core.applicators.allOf_basic': {
    description: allOf_basic_description,
    schema: allOf_basic_schema,
    datasets: allOf_basic_datasets,
  },
  'core.applicators.allOf_conflict': {
    description: allOf_conflict_description,
    schema: allOf_conflict_schema,
    datasets: allOf_conflict_datasets,
  },
  'core.applicators.anyOf_basic': {
    description: anyOf_basic_description,
    schema: anyOf_basic_schema,
    datasets: anyOf_basic_datasets,
  },
  'core.applicators.anyOf_multiple_valid': {
    description: anyOf_multiple_valid_description,
    schema: anyOf_multiple_valid_schema,
    datasets: anyOf_multiple_valid_datasets,
  },
  'core.applicators.oneOf_basic': {
    description: oneOf_basic_description,
    schema: oneOf_basic_schema,
    datasets: oneOf_basic_datasets,
  },
  'core.applicators.oneOf_type_variants': {
    description: oneOf_type_variants_description,
    schema: oneOf_type_variants_schema,
    datasets: oneOf_type_variants_datasets,
  },
  'core.applicators.not_basic': {
    description: not_basic_description,
    schema: not_basic_schema,
    datasets: not_basic_datasets,
  },
  'core.applicators.not_pattern': {
    description: not_pattern_description,
    schema: not_pattern_schema,
    datasets: not_pattern_datasets,
  },
} satisfies Record<
  CaseId,
  { description: string; schema: ConfigurationSchema; datasets: Record<string, ConfigurationData> }
>;

const meta = {
  title: 'uikit/ConfigurationEditor/ValidationCases/Core applicators',
  excludeStories: /.*CaseIds$/,
  argTypes: {
    caseId: {
      control: { type: 'select' },
      options: coreApplicatorsCaseIds,
    },
  },
  args: {
    caseId: coreApplicatorsCaseIds[0],
  },
} satisfies Meta<StoryArgs>;

export default meta;
type Story = StoryObj<StoryArgs>;

export const CoreApplicators = createValidationGroupStory({ cases }) satisfies Story;
