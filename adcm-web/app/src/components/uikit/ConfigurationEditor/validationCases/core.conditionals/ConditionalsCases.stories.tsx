import type { Meta, StoryObj } from '@storybook/react';
import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';
import { createValidationGroupStory, type ValidationGroupStoryArgs } from '../createValidationGroupStory';
import { if_then_basic_datasets, if_then_basic_description, if_then_basic_schema } from './if_then_basic.constants';
import {
  if_then_else_basic_datasets,
  if_then_else_basic_description,
  if_then_else_basic_schema,
} from './if_then_else_basic.constants';
import {
  if_present_then_missing_ok_datasets,
  if_present_then_missing_ok_description,
  if_present_then_missing_ok_schema,
} from './if_present_then_missing_ok.constants';
import {
  if_present_else_missing_ok_datasets,
  if_present_else_missing_ok_description,
  if_present_else_missing_ok_schema,
} from './if_present_else_missing_ok.constants';
import {
  if_only_no_effect_datasets,
  if_only_no_effect_description,
  if_only_no_effect_schema,
} from './if_only_no_effect.constants';
import {
  if_then_else_deep_nested_datasets,
  if_then_else_deep_nested_description,
  if_then_else_deep_nested_schema,
} from './if_then_else_deep_nested.constants';

export const coreConditionalsCaseIds = [
  'core.conditionals.if_then_basic',
  'core.conditionals.if_then_else_basic',
  'core.conditionals.if_present_then_missing_ok',
  'core.conditionals.if_present_else_missing_ok',
  'core.conditionals.if_only_no_effect',
  'core.conditionals.if_then_else_deep_nested',
] as const;

type CaseId = (typeof coreConditionalsCaseIds)[number];

type StoryArgs = ValidationGroupStoryArgs<CaseId>;

const cases = {
  'core.conditionals.if_then_basic': {
    description: if_then_basic_description,
    schema: if_then_basic_schema,
    datasets: if_then_basic_datasets,
  },
  'core.conditionals.if_then_else_basic': {
    description: if_then_else_basic_description,
    schema: if_then_else_basic_schema,
    datasets: if_then_else_basic_datasets,
  },
  'core.conditionals.if_present_then_missing_ok': {
    description: if_present_then_missing_ok_description,
    schema: if_present_then_missing_ok_schema,
    datasets: if_present_then_missing_ok_datasets,
  },
  'core.conditionals.if_present_else_missing_ok': {
    description: if_present_else_missing_ok_description,
    schema: if_present_else_missing_ok_schema,
    datasets: if_present_else_missing_ok_datasets,
  },
  'core.conditionals.if_only_no_effect': {
    description: if_only_no_effect_description,
    schema: if_only_no_effect_schema,
    datasets: if_only_no_effect_datasets,
  },
  'core.conditionals.if_then_else_deep_nested': {
    description: if_then_else_deep_nested_description,
    schema: if_then_else_deep_nested_schema,
    datasets: if_then_else_deep_nested_datasets,
  },
} satisfies Record<
  CaseId,
  { description: string; schema: ConfigurationSchema; datasets: Record<string, ConfigurationData> }
>;

const meta = {
  title: 'uikit/ConfigurationEditor/ValidationCases/Core conditionals',
  excludeStories: /.*CaseIds$/,
  argTypes: {
    caseId: {
      control: { type: 'select' },
      options: coreConditionalsCaseIds,
    },
  },
  args: {
    caseId: coreConditionalsCaseIds[0],
  },
} satisfies Meta<StoryArgs>;

export default meta;
type Story = StoryObj<StoryArgs>;

export const CoreConditionals = createValidationGroupStory({ cases }) satisfies Story;
