import type { Meta, StoryObj } from '@storybook/react';
import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';
import { createValidationGroupStory, type ValidationGroupStoryArgs } from '../createValidationGroupStory';
import {
  minLength_maxLength_datasets,
  minLength_maxLength_description,
  minLength_maxLength_schema,
} from './minLength_maxLength.constants';
import { pattern_datasets, pattern_description, pattern_schema } from './pattern.constants';
import { enum_const_datasets, enum_const_description, enum_const_schema } from './enum_const.constants';

export const validationStringsCaseIds = [
  'validation.strings.minLength_maxLength',
  'validation.strings.pattern',
  'validation.strings.enum_const',
] as const;

type CaseId = (typeof validationStringsCaseIds)[number];
type StoryArgs = ValidationGroupStoryArgs<CaseId>;

const cases = {
  'validation.strings.minLength_maxLength': {
    description: minLength_maxLength_description,
    schema: minLength_maxLength_schema,
    datasets: minLength_maxLength_datasets,
  },
  'validation.strings.pattern': {
    description: pattern_description,
    schema: pattern_schema,
    datasets: pattern_datasets,
  },
  'validation.strings.enum_const': {
    description: enum_const_description,
    schema: enum_const_schema,
    datasets: enum_const_datasets,
  },
} satisfies Record<
  CaseId,
  { description: string; schema: ConfigurationSchema; datasets: Record<string, ConfigurationData> }
>;

const meta = {
  title: 'uikit/ConfigurationEditor/ValidationCases/Validation strings',
  excludeStories: /.*CaseIds$/,
  argTypes: {
    caseId: {
      control: { type: 'select' },
      options: validationStringsCaseIds,
    },
  },
  args: {
    caseId: validationStringsCaseIds[0],
  },
} satisfies Meta<StoryArgs>;

export default meta;
type Story = StoryObj<StoryArgs>;

export const ValidationStrings = createValidationGroupStory({ cases }) satisfies Story;
