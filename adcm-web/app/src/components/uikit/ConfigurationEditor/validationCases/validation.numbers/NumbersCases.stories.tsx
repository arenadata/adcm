import type { Meta, StoryObj } from '@storybook/react';
import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';
import { createValidationGroupStory, type ValidationGroupStoryArgs } from '../createValidationGroupStory';
import {
  minimum_maximum_datasets,
  minimum_maximum_description,
  minimum_maximum_schema,
} from './minimum_maximum.constants';
import {
  exclusive_bounds_datasets,
  exclusive_bounds_description,
  exclusive_bounds_schema,
} from './exclusive_bounds.constants';
import { multipleOf_datasets, multipleOf_description, multipleOf_schema } from './multipleOf.constants';
import { enum_const_datasets, enum_const_description, enum_const_schema } from './enum_const.constants';
import {
  integer_vs_number_datasets,
  integer_vs_number_description,
  integer_vs_number_schema,
} from './integer_vs_number.constants';
import {
  minimum_multipleOf_datasets,
  minimum_multipleOf_description,
  minimum_multipleOf_schema,
} from './minimum_multipleOf.constants';

export const validationNumbersCaseIds = [
  'validation.numbers.minimum_maximum',
  'validation.numbers.exclusive_bounds',
  'validation.numbers.multipleOf',
  'validation.numbers.enum_const',
  'validation.numbers.integer_vs_number',
  'validation.numbers.minimum_multipleOf',
] as const;

type CaseId = (typeof validationNumbersCaseIds)[number];
type StoryArgs = ValidationGroupStoryArgs<CaseId>;

const cases = {
  'validation.numbers.minimum_maximum': {
    description: minimum_maximum_description,
    schema: minimum_maximum_schema,
    datasets: minimum_maximum_datasets,
  },
  'validation.numbers.exclusive_bounds': {
    description: exclusive_bounds_description,
    schema: exclusive_bounds_schema,
    datasets: exclusive_bounds_datasets,
  },
  'validation.numbers.multipleOf': {
    description: multipleOf_description,
    schema: multipleOf_schema,
    datasets: multipleOf_datasets,
  },
  'validation.numbers.enum_const': {
    description: enum_const_description,
    schema: enum_const_schema,
    datasets: enum_const_datasets,
  },
  'validation.numbers.integer_vs_number': {
    description: integer_vs_number_description,
    schema: integer_vs_number_schema,
    datasets: integer_vs_number_datasets,
  },
  'validation.numbers.minimum_multipleOf': {
    description: minimum_multipleOf_description,
    schema: minimum_multipleOf_schema,
    datasets: minimum_multipleOf_datasets,
  },
} satisfies Record<
  CaseId,
  { description: string; schema: ConfigurationSchema; datasets: Record<string, ConfigurationData> }
>;

const meta = {
  title: 'uikit/ConfigurationEditor/ValidationCases/Validation numbers',
  excludeStories: /.*CaseIds$/,
  argTypes: {
    caseId: {
      control: { type: 'select' },
      options: validationNumbersCaseIds,
    },
  },
  args: {
    caseId: validationNumbersCaseIds[0],
  },
} satisfies Meta<StoryArgs>;

export default meta;
type Story = StoryObj<StoryArgs>;

export const ValidationNumbers = createValidationGroupStory({ cases }) satisfies Story;
