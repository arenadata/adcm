import type React from 'react';
import s from './ActionWizardMap.module.scss';
import MapItemStages from '@uikit/ActionWizardMap/ActionWizardMapItem/ActionWizardMapItem';
import type { AdcmActionWizardProcess } from '@models/adcm/wizard';

interface ActionWizardMapProps {
  process: AdcmActionWizardProcess;
}

const ActionWizardMap: React.FC<ActionWizardMapProps> = ({ process }: ActionWizardMapProps) => {
  return (
    <div>
      <div className={s.actionWizardMap__title}>Manage install</div>
      <div className={s.actionWizardMap}>
        <MapItemStages process={process} />
      </div>
    </div>
  );
};

export default ActionWizardMap;
