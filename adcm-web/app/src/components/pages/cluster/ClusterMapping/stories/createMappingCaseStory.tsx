import type { StoryObj } from '@storybook/react';
import { MappingCaseRunner } from './MappingCaseRunner';
import type { MappingStoryCase } from './mappingStory.types';

export type MappingGroupStoryArgs<CaseId extends string> = {
  caseId: CaseId;
};

export function createMappingCaseStory<CaseId extends string>({
  cases,
}: {
  cases: Record<CaseId, MappingStoryCase>;
}): StoryObj<MappingGroupStoryArgs<CaseId>> {
  return {
    render: (args: MappingGroupStoryArgs<CaseId>) => <MappingCaseRunner caseId={args.caseId} cases={cases} />,
  };
}
