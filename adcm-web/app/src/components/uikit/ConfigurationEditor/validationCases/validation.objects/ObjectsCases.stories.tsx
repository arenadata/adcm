import type { Meta, StoryObj } from '@storybook/react';
import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';
import { createValidationGroupStory, type ValidationGroupStoryArgs } from '../createValidationGroupStory';
import {
  minProperties_maxProperties_datasets,
  minProperties_maxProperties_description,
  minProperties_maxProperties_schema,
} from './minProperties_maxProperties.constants';
import { required_keys_datasets, required_keys_description, required_keys_schema } from './required_keys.constants';
import {
  additionalProperties_false_datasets,
  additionalProperties_false_description,
  additionalProperties_false_schema,
} from './additionalProperties_false.constants';
import {
  patternProperties_datasets,
  patternProperties_description,
  patternProperties_schema,
} from './patternProperties.constants';
import { propertyNames_datasets, propertyNames_description, propertyNames_schema } from './propertyNames.constants';
import {
  unevaluatedProperties_false_datasets,
  unevaluatedProperties_false_description,
  unevaluatedProperties_false_schema,
} from './unevaluatedProperties_false.constants';
import {
  mixed_props_pattern_unevaluated_datasets,
  mixed_props_pattern_unevaluated_description,
  mixed_props_pattern_unevaluated_schema,
} from './mixed_props_pattern_unevaluated.constants';
import {
  nested_required_chain_datasets,
  nested_required_chain_description,
  nested_required_chain_schema,
} from './nested_required_chain.constants';

export const validationObjectsCaseIds = [
  'validation.objects.minProperties_maxProperties',
  'validation.objects.required_keys',
  'validation.objects.additionalProperties_false',
  'validation.objects.patternProperties',
  'validation.objects.propertyNames',
  'validation.objects.unevaluatedProperties_false',
  'validation.objects.mixed_props_pattern_unevaluated',
  'validation.objects.nested_required_chain',
] as const;

type CaseId = (typeof validationObjectsCaseIds)[number];
type StoryArgs = ValidationGroupStoryArgs<CaseId>;

const cases = {
  'validation.objects.minProperties_maxProperties': {
    description: minProperties_maxProperties_description,
    schema: minProperties_maxProperties_schema,
    datasets: minProperties_maxProperties_datasets,
  },
  'validation.objects.required_keys': {
    description: required_keys_description,
    schema: required_keys_schema,
    datasets: required_keys_datasets,
  },
  'validation.objects.additionalProperties_false': {
    description: additionalProperties_false_description,
    schema: additionalProperties_false_schema,
    datasets: additionalProperties_false_datasets,
  },
  'validation.objects.patternProperties': {
    description: patternProperties_description,
    schema: patternProperties_schema,
    datasets: patternProperties_datasets,
  },
  'validation.objects.propertyNames': {
    description: propertyNames_description,
    schema: propertyNames_schema,
    datasets: propertyNames_datasets,
  },
  'validation.objects.unevaluatedProperties_false': {
    description: unevaluatedProperties_false_description,
    schema: unevaluatedProperties_false_schema,
    datasets: unevaluatedProperties_false_datasets,
  },
  'validation.objects.mixed_props_pattern_unevaluated': {
    description: mixed_props_pattern_unevaluated_description,
    schema: mixed_props_pattern_unevaluated_schema,
    datasets: mixed_props_pattern_unevaluated_datasets,
  },
  'validation.objects.nested_required_chain': {
    description: nested_required_chain_description,
    schema: nested_required_chain_schema,
    datasets: nested_required_chain_datasets,
  },
} satisfies Record<
  CaseId,
  { description: string; schema: ConfigurationSchema; datasets: Record<string, ConfigurationData> }
>;

const meta = {
  title: 'uikit/ConfigurationEditor/ValidationCases/Validation objects',
  excludeStories: /.*CaseIds$/,
  argTypes: {
    caseId: {
      control: { type: 'select' },
      options: validationObjectsCaseIds,
    },
  },
  args: {
    caseId: validationObjectsCaseIds[0],
  },
} satisfies Meta<StoryArgs>;

export default meta;
type Story = StoryObj<StoryArgs>;

export const ValidationObjects = createValidationGroupStory({ cases }) satisfies Story;
