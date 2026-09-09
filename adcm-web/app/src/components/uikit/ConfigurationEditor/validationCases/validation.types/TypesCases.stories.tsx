import type { Meta, StoryObj } from '@storybook/react';
import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';
import { createValidationGroupStory, type ValidationGroupStoryArgs } from '../createValidationGroupStory';
import { string_or_null_datasets, string_or_null_description, string_or_null_schema } from './string_or_null.constants';
import { null_only_datasets, null_only_description, null_only_schema } from './null_only.constants';
import {
  integer_or_string_datasets,
  integer_or_string_description,
  integer_or_string_schema,
} from './integer_or_string.constants';

export const validationTypesCaseIds = [
  'validation.types.string_or_null',
  'validation.types.null_only',
  'validation.types.integer_or_string',
] as const;

type CaseId = (typeof validationTypesCaseIds)[number];
type StoryArgs = ValidationGroupStoryArgs<CaseId>;

const cases = {
  'validation.types.string_or_null': {
    description: string_or_null_description,
    schema: string_or_null_schema,
    datasets: string_or_null_datasets,
  },
  'validation.types.null_only': {
    description: null_only_description,
    schema: null_only_schema,
    datasets: null_only_datasets,
  },
  'validation.types.integer_or_string': {
    description: integer_or_string_description,
    schema: integer_or_string_schema,
    datasets: integer_or_string_datasets,
  },
} satisfies Record<
  CaseId,
  { description: string; schema: ConfigurationSchema; datasets: Record<string, ConfigurationData> }
>;

const meta = {
  title: 'uikit/ConfigurationEditor/ValidationCases/Validation types',
  excludeStories: /.*CaseIds$/,
  argTypes: {
    caseId: {
      control: { type: 'select' },
      options: validationTypesCaseIds,
    },
  },
  args: {
    caseId: validationTypesCaseIds[0],
  },
} satisfies Meta<StoryArgs>;

export default meta;
type Story = StoryObj<StoryArgs>;

export const ValidationTypes = createValidationGroupStory({ cases }) satisfies Story;
