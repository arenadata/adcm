import type { Meta, StoryObj } from '@storybook/react';
import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';
import { createValidationGroupStory, type ValidationGroupStoryArgs } from '../createValidationGroupStory';
import {
  dependentRequired_basic_datasets,
  dependentRequired_basic_description,
  dependentRequired_basic_schema,
} from './dependentRequired_basic.constants';
import {
  dependentRequired_multiple_keys_datasets,
  dependentRequired_multiple_keys_description,
  dependentRequired_multiple_keys_schema,
} from './dependentRequired_multiple_keys.constants';
import {
  dependentSchemas_additional_constraints_datasets,
  dependentSchemas_additional_constraints_description,
  dependentSchemas_additional_constraints_schema,
} from './dependentSchemas_additional_constraints.constants';
import {
  dependentSchemas_schema_branching_datasets,
  dependentSchemas_schema_branching_description,
  dependentSchemas_schema_branching_schema,
} from './dependentSchemas_schema_branching.constants';
import {
  dependentRequired_with_required_interaction_datasets,
  dependentRequired_with_required_interaction_description,
  dependentRequired_with_required_interaction_schema,
} from './dependentRequired_with_required_interaction.constants';

export const coreDepsCaseIds = [
  'core.deps.dependentRequired_basic',
  'core.deps.dependentRequired_multiple_keys',
  'core.deps.dependentSchemas_additional_constraints',
  'core.deps.dependentSchemas_schema_branching',
  'core.deps.dependentSchemas_required_interaction',
] as const;

type CaseId = (typeof coreDepsCaseIds)[number];
type StoryArgs = ValidationGroupStoryArgs<CaseId>;

const cases = {
  'core.deps.dependentRequired_basic': {
    description: dependentRequired_basic_description,
    schema: dependentRequired_basic_schema,
    datasets: dependentRequired_basic_datasets,
  },
  'core.deps.dependentRequired_multiple_keys': {
    description: dependentRequired_multiple_keys_description,
    schema: dependentRequired_multiple_keys_schema,
    datasets: dependentRequired_multiple_keys_datasets,
  },
  'core.deps.dependentSchemas_additional_constraints': {
    description: dependentSchemas_additional_constraints_description,
    schema: dependentSchemas_additional_constraints_schema,
    datasets: dependentSchemas_additional_constraints_datasets,
  },
  'core.deps.dependentSchemas_schema_branching': {
    description: dependentSchemas_schema_branching_description,
    schema: dependentSchemas_schema_branching_schema,
    datasets: dependentSchemas_schema_branching_datasets,
  },
  'core.deps.dependentSchemas_required_interaction': {
    description: dependentRequired_with_required_interaction_description,
    schema: dependentRequired_with_required_interaction_schema,
    datasets: dependentRequired_with_required_interaction_datasets,
  },
} satisfies Record<
  CaseId,
  { description: string; schema: ConfigurationSchema; datasets: Record<string, ConfigurationData> }
>;

const meta = {
  title: 'uikit/ConfigurationEditor/ValidationCases/Core deps',
  excludeStories: /.*CaseIds$/,
  argTypes: {
    caseId: {
      control: { type: 'select' },
      options: coreDepsCaseIds,
    },
  },
  args: {
    caseId: coreDepsCaseIds[0],
  },
} satisfies Meta<StoryArgs>;

export default meta;
type Story = StoryObj<StoryArgs>;

export const CoreDeps = createValidationGroupStory({ cases }) satisfies Story;
