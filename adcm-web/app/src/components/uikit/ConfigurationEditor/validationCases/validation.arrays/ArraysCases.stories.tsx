import type { Meta, StoryObj } from '@storybook/react';
import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';
import { createValidationGroupStory, type ValidationGroupStoryArgs } from '../createValidationGroupStory';
import { contains_basic_datasets, contains_basic_description, contains_basic_schema } from './contains_basic.constants';
import {
  contains_minContains_2_datasets,
  contains_minContains_2_description,
  contains_minContains_2_schema,
} from './contains_minContains_2.constants';
import {
  contains_maxContains_1_datasets,
  contains_maxContains_1_description,
  contains_maxContains_1_schema,
} from './contains_maxContains_1.constants';
import {
  uniqueItems_simple_datasets,
  uniqueItems_simple_description,
  uniqueItems_simple_schema,
} from './uniqueItems_simple.constants';
import {
  prefixItems_tuple_items_false_datasets,
  prefixItems_tuple_items_false_description,
  prefixItems_tuple_items_false_schema,
} from './prefixItems_tuple_items_false.constants';
import {
  prefixItems_items_after_prefix_datasets,
  prefixItems_items_after_prefix_description,
  prefixItems_items_after_prefix_schema,
} from './prefixItems_items_after_prefix.constants';
import {
  minItems_maxItems_datasets,
  minItems_maxItems_description,
  minItems_maxItems_schema,
} from './minItems_maxItems.constants';
import {
  items_false_disallow_any_datasets,
  items_false_disallow_any_description,
  items_false_disallow_any_schema,
} from './items_false_disallow_any.constants';
import {
  additionalItems_disallow_extra_datasets,
  additionalItems_disallow_extra_description,
  additionalItems_disallow_extra_schema,
} from './additionalItems_disallow_extra.constants';
import {
  unevaluatedItems_false_disallow_extra_datasets,
  unevaluatedItems_false_disallow_extra_description,
  unevaluatedItems_false_disallow_extra_schema,
} from './unevaluatedItems_false_disallow_extra.constants';
import {
  items_wrong_element_type_datasets,
  items_wrong_element_type_description,
  items_wrong_element_type_schema,
} from './items_wrong_element_type.constants';
import {
  minItems_1_empty_array_datasets,
  minItems_1_empty_array_description,
  minItems_1_empty_array_schema,
} from './minItems_1_empty_array.constants';

export const validationArraysCaseIds = [
  'validation.arrays.contains_basic',
  'validation.arrays.contains_minContains_2',
  'validation.arrays.contains_maxContains_1',
  'validation.arrays.uniqueItems_simple',
  'validation.arrays.prefixItems_tuple_items_false',
  'validation.arrays.prefixItems_items_after_prefix',
  'validation.arrays.minItems_maxItems',
  'validation.arrays.items_false_disallow_any',
  'validation.arrays.additionalItems_disallow_extra',
  'validation.arrays.unevaluatedItems_false_disallow_extra',
  'validation.arrays.items_wrong_element_type',
  'validation.arrays.minItems_1_empty_array',
] as const;

type CaseId = (typeof validationArraysCaseIds)[number];
type StoryArgs = ValidationGroupStoryArgs<CaseId>;

const cases = {
  'validation.arrays.contains_basic': {
    description: contains_basic_description,
    schema: contains_basic_schema,
    datasets: contains_basic_datasets,
  },
  'validation.arrays.contains_minContains_2': {
    description: contains_minContains_2_description,
    schema: contains_minContains_2_schema,
    datasets: contains_minContains_2_datasets,
  },
  'validation.arrays.contains_maxContains_1': {
    description: contains_maxContains_1_description,
    schema: contains_maxContains_1_schema,
    datasets: contains_maxContains_1_datasets,
  },
  'validation.arrays.uniqueItems_simple': {
    description: uniqueItems_simple_description,
    schema: uniqueItems_simple_schema,
    datasets: uniqueItems_simple_datasets,
  },
  'validation.arrays.prefixItems_tuple_items_false': {
    description: prefixItems_tuple_items_false_description,
    schema: prefixItems_tuple_items_false_schema,
    datasets: prefixItems_tuple_items_false_datasets,
  },
  'validation.arrays.prefixItems_items_after_prefix': {
    description: prefixItems_items_after_prefix_description,
    schema: prefixItems_items_after_prefix_schema,
    datasets: prefixItems_items_after_prefix_datasets,
  },
  'validation.arrays.minItems_maxItems': {
    description: minItems_maxItems_description,
    schema: minItems_maxItems_schema,
    datasets: minItems_maxItems_datasets,
  },
  'validation.arrays.items_false_disallow_any': {
    description: items_false_disallow_any_description,
    schema: items_false_disallow_any_schema,
    datasets: items_false_disallow_any_datasets,
  },
  'validation.arrays.additionalItems_disallow_extra': {
    description: additionalItems_disallow_extra_description,
    schema: additionalItems_disallow_extra_schema,
    datasets: additionalItems_disallow_extra_datasets,
  },
  'validation.arrays.unevaluatedItems_false_disallow_extra': {
    description: unevaluatedItems_false_disallow_extra_description,
    schema: unevaluatedItems_false_disallow_extra_schema,
    datasets: unevaluatedItems_false_disallow_extra_datasets,
  },
  'validation.arrays.items_wrong_element_type': {
    description: items_wrong_element_type_description,
    schema: items_wrong_element_type_schema,
    datasets: items_wrong_element_type_datasets,
  },
  'validation.arrays.minItems_1_empty_array': {
    description: minItems_1_empty_array_description,
    schema: minItems_1_empty_array_schema,
    datasets: minItems_1_empty_array_datasets,
  },
} satisfies Record<
  CaseId,
  { description: string; schema: ConfigurationSchema; datasets: Record<string, ConfigurationData> }
>;

const meta = {
  title: 'uikit/ConfigurationEditor/ValidationCases/Validation arrays',
  excludeStories: /.*CaseIds$/,
  argTypes: {
    caseId: {
      control: { type: 'select' },
      options: validationArraysCaseIds,
    },
  },
  args: {
    caseId: validationArraysCaseIds[0],
  },
} satisfies Meta<StoryArgs>;

export default meta;
type Story = StoryObj<StoryArgs>;

export const ValidationArrays = createValidationGroupStory({ cases }) satisfies Story;
