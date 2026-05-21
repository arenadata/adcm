import type { StoryObj } from '@storybook/react';
import { ValidationCaseRunner, type ValidationCase } from './ValidationCaseRunner';

export type ValidationGroupStoryArgs<CaseId extends string> = {
  caseId: CaseId;
};

export function createValidationGroupStory<CaseId extends string>({
  cases,
}: {
  cases: Record<CaseId, ValidationCase>;
}): StoryObj<ValidationGroupStoryArgs<CaseId>> {
  return {
    render: (args: ValidationGroupStoryArgs<CaseId>) => <ValidationCaseRunner caseId={args.caseId} cases={cases} />,
  };
}
