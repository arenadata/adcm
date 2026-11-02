import { MappingScene } from './MappingScene';
import type { MappingStoryCase } from './mappingStory.types';

type MappingCaseRunnerProps<CaseId extends string> = {
  caseId: CaseId;
  cases: Record<CaseId, MappingStoryCase>;
};

export const MappingCaseRunner = <CaseId extends string>({ caseId, cases }: MappingCaseRunnerProps<CaseId>) => {
  const storyCase = cases[caseId];
  if (!storyCase) {
    return <div>Unknown mapping story case: {String(caseId)}</div>;
  }

  return (
    <MappingScene
      key={caseId}
      view={storyCase.kind}
      description={storyCase.description}
      pairs={storyCase.pairs}
      hosts={storyCase.hosts}
      components={storyCase.components}
      notAddedServicesDictionary={storyCase.notAddedServicesDictionary}
      focusComponentName={storyCase.focusComponentName}
      focusHostName={storyCase.focusHostName}
      layout={storyCase.layout}
      dialog={storyCase.dialog}
      rules={storyCase.rules}
      hostsPreviewMode={storyCase.hostsPreviewMode}
    />
  );
};
