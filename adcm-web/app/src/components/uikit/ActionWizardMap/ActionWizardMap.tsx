import type React from 'react';
import s from './ActionWizardMap.module.scss';
import MapItemStages from '@uikit/ActionWizardMap/ActionWizardMapItem/ActionWizardMapItem';
import type { AdcmActionWizardProcess, AdcmWizardJobsData } from '@models/adcm/wizard';

interface ActionWizardMapProps {
  process: AdcmActionWizardProcess;
  wizardTitle: string;
  jobsData: AdcmWizardJobsData;
  selectedStep: number;
  onSetBrokenStepError: (error?: string) => void;
  onSetSelectedStepId: (id: number) => void;
}

const ActionWizardMap: React.FC<ActionWizardMapProps> = ({
  process,
  wizardTitle,
  jobsData,
  selectedStep,
  onSetBrokenStepError,
  onSetSelectedStepId,
}: ActionWizardMapProps) => {
  return (
    <div>
      <div className={s.actionWizardMap__title}>{wizardTitle}</div>
      <div className={s.actionWizardMap}>
        <MapItemStages
          process={process}
          jobsData={jobsData}
          selectedStep={selectedStep}
          onSetBrokenStepError={onSetBrokenStepError}
          onSetSelectedStepId={onSetSelectedStepId}
        />
      </div>
    </div>
  );
};

export default ActionWizardMap;
