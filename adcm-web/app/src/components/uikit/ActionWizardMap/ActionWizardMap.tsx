import type React from 'react';
import s from './ActionWizardMap.module.scss';
import MapItemStages from '@uikit/ActionWizardMap/ActionWizardMapItem/ActionWizardMapItem';
import type { AdcmActionWizardProcess } from '@models/adcm/wizard';

interface ActionWizardMapProps {
  process: AdcmActionWizardProcess;
  wizardTitle: string;
}

const ActionWizardMap: React.FC<ActionWizardMapProps> = ({ process, wizardTitle }: ActionWizardMapProps) => {
  return (
    <div>
      <div className={s.actionWizardMap__title}>{wizardTitle}</div>
      <div className={s.actionWizardMap}>
        <MapItemStages process={process} />
      </div>
    </div>
  );
};

export default ActionWizardMap;
