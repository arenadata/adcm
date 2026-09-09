import type { Meta, StoryObj } from '@storybook/react';
import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';
import { createValidationGroupStory, type ValidationGroupStoryArgs } from '../createValidationGroupStory';
import {
  discriminator_missing_or_unknown_datasets,
  discriminator_missing_or_unknown_description,
  discriminator_missing_or_unknown_schema,
} from './discriminator_missing_or_unknown.constants';
import {
  discriminator_switch_branch_leftovers_datasets,
  discriminator_switch_branch_leftovers_description,
  discriminator_switch_branch_leftovers_schema,
} from './discriminator_switch_branch_leftovers.constants';
import {
  discriminator_nested_path_datasets,
  discriminator_nested_path_description,
  discriminator_nested_path_schema,
} from './discriminator_nested_path.constants';
import {
  discriminator_branch_required_path_datasets,
  discriminator_branch_required_path_description,
  discriminator_branch_required_path_schema,
} from './discriminator_branch_required_path.constants';
import {
  discriminator_nested_switch_leftovers_datasets,
  discriminator_nested_switch_leftovers_description,
  discriminator_nested_switch_leftovers_schema,
} from './discriminator_nested_switch_leftovers.constants';
import {
  discriminator_value_not_in_mapping_datasets,
  discriminator_value_not_in_mapping_description,
  discriminator_value_not_in_mapping_schema,
} from './discriminator_value_not_in_mapping.constants';
import {
  nullable_discriminator_object_datasets,
  nullable_discriminator_object_description,
  nullable_discriminator_object_schema,
} from './nullable_discriminator_object.constants';
import {
  discriminator_null_forbidden_datasets,
  discriminator_null_forbidden_description,
  discriminator_null_forbidden_schema,
} from './discriminator_null_forbidden.constants';
import {
  oneOf_nullable_array_datasets,
  oneOf_nullable_array_description,
  oneOf_nullable_array_schema,
} from './oneOf_nullable_array.constants';
import {
  oneOf_many_variants_datasets,
  oneOf_many_variants_description,
  oneOf_many_variants_schema,
} from './oneOf_many_variants.constants';
import {
  oneOf_discriminator_basic_datasets,
  oneOf_discriminator_basic_description,
  oneOf_discriminator_basic_schema,
} from './oneOf_discriminator_basic.constants';

export const coreDiscriminatorCaseIds = [
  'core.discriminator.missing_or_unknown',
  'core.discriminator.switch_branch_leftovers',
  'core.discriminator.nested_path',
  'core.discriminator.branch_required_leaf_path',
  'core.discriminator.nested_switch_leftovers',
  'core.discriminator.value_not_in_mapping',
  'core.discriminator.nullable_variant',
  'core.discriminator.null_forbidden',
  'core.discriminator.oneOf_nullable_array',
  'core.discriminator.oneOf_many_variants',
  'core.discriminator.oneOf_discriminator_basic',
] as const;

type CaseId = (typeof coreDiscriminatorCaseIds)[number];
type StoryArgs = ValidationGroupStoryArgs<CaseId>;

const cases = {
  'core.discriminator.missing_or_unknown': {
    description: discriminator_missing_or_unknown_description,
    schema: discriminator_missing_or_unknown_schema,
    datasets: discriminator_missing_or_unknown_datasets,
  },
  'core.discriminator.switch_branch_leftovers': {
    description: discriminator_switch_branch_leftovers_description,
    schema: discriminator_switch_branch_leftovers_schema,
    datasets: discriminator_switch_branch_leftovers_datasets,
  },
  'core.discriminator.nested_path': {
    description: discriminator_nested_path_description,
    schema: discriminator_nested_path_schema,
    datasets: discriminator_nested_path_datasets,
  },
  'core.discriminator.branch_required_leaf_path': {
    description: discriminator_branch_required_path_description,
    schema: discriminator_branch_required_path_schema,
    datasets: discriminator_branch_required_path_datasets,
  },
  'core.discriminator.nested_switch_leftovers': {
    description: discriminator_nested_switch_leftovers_description,
    schema: discriminator_nested_switch_leftovers_schema,
    datasets: discriminator_nested_switch_leftovers_datasets,
  },
  'core.discriminator.value_not_in_mapping': {
    description: discriminator_value_not_in_mapping_description,
    schema: discriminator_value_not_in_mapping_schema,
    datasets: discriminator_value_not_in_mapping_datasets,
  },
  'core.discriminator.nullable_variant': {
    description: nullable_discriminator_object_description,
    schema: nullable_discriminator_object_schema,
    datasets: nullable_discriminator_object_datasets,
  },
  'core.discriminator.null_forbidden': {
    description: discriminator_null_forbidden_description,
    schema: discriminator_null_forbidden_schema,
    datasets: discriminator_null_forbidden_datasets,
  },
  'core.discriminator.oneOf_nullable_array': {
    description: oneOf_nullable_array_description,
    schema: oneOf_nullable_array_schema,
    datasets: oneOf_nullable_array_datasets,
  },
  'core.discriminator.oneOf_many_variants': {
    description: oneOf_many_variants_description,
    schema: oneOf_many_variants_schema,
    datasets: oneOf_many_variants_datasets,
  },
  'core.discriminator.oneOf_discriminator_basic': {
    description: oneOf_discriminator_basic_description,
    schema: oneOf_discriminator_basic_schema,
    datasets: oneOf_discriminator_basic_datasets,
  },
} satisfies Record<
  CaseId,
  { description: string; schema: ConfigurationSchema; datasets: Record<string, ConfigurationData> }
>;

const meta = {
  title: 'uikit/ConfigurationEditor/ValidationCases/Core discriminator',
  excludeStories: /.*CaseIds$/,
  argTypes: {
    caseId: {
      control: { type: 'select' },
      options: coreDiscriminatorCaseIds,
    },
  },
  args: {
    caseId: coreDiscriminatorCaseIds[0],
  },
} satisfies Meta<StoryArgs>;

export default meta;
type Story = StoryObj<StoryArgs>;

export const CoreDiscriminator = createValidationGroupStory({ cases }) satisfies Story;
