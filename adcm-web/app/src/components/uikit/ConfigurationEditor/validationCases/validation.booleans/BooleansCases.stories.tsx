import type { Meta, StoryObj } from '@storybook/react';
import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';
import { createValidationGroupStory, type ValidationGroupStoryArgs } from '../createValidationGroupStory';
import { type_boolean_datasets, type_boolean_description, type_boolean_schema } from './type_boolean.constants';
import { const_true_datasets, const_true_description, const_true_schema } from './const_true.constants';
import { enum_boolean_datasets, enum_boolean_description, enum_boolean_schema } from './enum_boolean.constants';

export const validationBooleansCaseIds = [
  'validation.booleans.type_boolean',
  'validation.booleans.const_true',
  'validation.booleans.enum_true_false',
] as const;

type CaseId = (typeof validationBooleansCaseIds)[number];
type StoryArgs = ValidationGroupStoryArgs<CaseId>;

const cases = {
  'validation.booleans.type_boolean': {
    description: type_boolean_description,
    schema: type_boolean_schema,
    datasets: type_boolean_datasets,
  },
  'validation.booleans.const_true': {
    description: const_true_description,
    schema: const_true_schema,
    datasets: const_true_datasets,
  },
  'validation.booleans.enum_true_false': {
    description: enum_boolean_description,
    schema: enum_boolean_schema,
    datasets: enum_boolean_datasets,
  },
} satisfies Record<
  CaseId,
  { description: string; schema: ConfigurationSchema; datasets: Record<string, ConfigurationData> }
>;

const meta = {
  title: 'uikit/ConfigurationEditor/ValidationCases/Validation booleans',
  excludeStories: /.*CaseIds$/,
  argTypes: {
    caseId: {
      control: { type: 'select' },
      options: validationBooleansCaseIds,
    },
  },
  args: {
    caseId: validationBooleansCaseIds[0],
  },
} satisfies Meta<StoryArgs>;

export default meta;
type Story = StoryObj<StoryArgs>;

export const ValidationBooleans = createValidationGroupStory({ cases }) satisfies Story;
