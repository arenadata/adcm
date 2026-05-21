import type { Meta, StoryObj } from '@storybook/react';
import type { ValidationCase } from '../ValidationCaseRunner';
import { createValidationGroupStory, type ValidationGroupStoryArgs } from '../createValidationGroupStory';
import {
  readonly_minLength_datasets,
  readonly_minLength_description,
  readonly_minLength_schema,
} from './readonly_minLength.constants';
import {
  secret_pattern_vault_datasets,
  secret_pattern_vault_description,
  secret_pattern_vault_schema,
} from './secret_pattern_vault.constants';
import {
  inactive_group_attributesByDataset,
  inactive_group_datasets,
  inactive_group_description,
  inactive_group_schema,
} from './inactive_group.constants';
import {
  secret_minMax_vault_datasets,
  secret_minMax_vault_description,
  secret_minMax_vault_schema,
} from './secret_minMax_vault.constants';
import {
  secret_vault_like_not_prefix_datasets,
  secret_vault_like_not_prefix_description,
  secret_vault_like_not_prefix_schema,
} from './secret_vault_like_not_prefix.constants';
import {
  inactive_group_deep_path_attributesByDataset,
  inactive_group_deep_path_datasets,
  inactive_group_deep_path_description,
  inactive_group_deep_path_schema,
} from './inactive_group_deep_path.constants';
import {
  synchronized_readonly_ui_attributesByDataset,
  synchronized_readonly_ui_datasets,
  synchronized_readonly_ui_description,
  synchronized_readonly_ui_schema,
} from './synchronized_readonly_ui.constants';

export const validationMetaCaseIds = [
  'validation.meta.readonly_minLength',
  'validation.meta.secret_pattern_vs_vault',
  'validation.meta.inactive_group_errors',
  'validation.meta.secret_minMax_vault',
  'validation.meta.secret_vault_like_not_prefix',
  'validation.meta.inactive_group_deep_path',
  'validation.meta.synchronized_readonly_ui',
] as const;

type CaseId = (typeof validationMetaCaseIds)[number];
type StoryArgs = ValidationGroupStoryArgs<CaseId>;

const cases = {
  'validation.meta.readonly_minLength': {
    description: readonly_minLength_description,
    schema: readonly_minLength_schema,
    datasets: readonly_minLength_datasets,
  },
  'validation.meta.secret_pattern_vs_vault': {
    description: secret_pattern_vault_description,
    schema: secret_pattern_vault_schema,
    datasets: secret_pattern_vault_datasets,
  },
  'validation.meta.inactive_group_errors': {
    description: inactive_group_description,
    schema: inactive_group_schema,
    datasets: inactive_group_datasets,
    attributesByDataset: inactive_group_attributesByDataset,
  },
  'validation.meta.secret_minMax_vault': {
    description: secret_minMax_vault_description,
    schema: secret_minMax_vault_schema,
    datasets: secret_minMax_vault_datasets,
  },
  'validation.meta.secret_vault_like_not_prefix': {
    description: secret_vault_like_not_prefix_description,
    schema: secret_vault_like_not_prefix_schema,
    datasets: secret_vault_like_not_prefix_datasets,
  },
  'validation.meta.inactive_group_deep_path': {
    description: inactive_group_deep_path_description,
    schema: inactive_group_deep_path_schema,
    datasets: inactive_group_deep_path_datasets,
    attributesByDataset: inactive_group_deep_path_attributesByDataset,
  },
  'validation.meta.synchronized_readonly_ui': {
    description: synchronized_readonly_ui_description,
    schema: synchronized_readonly_ui_schema,
    datasets: synchronized_readonly_ui_datasets,
    attributesByDataset: synchronized_readonly_ui_attributesByDataset,
  },
} satisfies Record<CaseId, ValidationCase>;

const meta = {
  title: 'uikit/ConfigurationEditor/ValidationCases/Validation meta',
  excludeStories: /.*CaseIds$/,
  argTypes: {
    caseId: {
      control: { type: 'select' },
      options: validationMetaCaseIds,
    },
  },
  args: {
    caseId: validationMetaCaseIds[0],
  },
} satisfies Meta<StoryArgs>;

export default meta;
type Story = StoryObj<StoryArgs>;

export const ValidationMeta = createValidationGroupStory({ cases }) satisfies Story;
