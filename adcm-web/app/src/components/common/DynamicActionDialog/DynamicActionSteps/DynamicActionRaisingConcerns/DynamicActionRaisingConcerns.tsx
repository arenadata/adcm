import { useState } from 'react';
import { Button, ButtonGroup, Switch, WarningMessage } from '@uikit';
import type { AdcmDynamicActionDetails, AdcmDynamicActionRunConfig } from '@models/adcm';
import dialogStyles from '../../DynamicActionDialog.module.scss';
import s from './DynamicActionRaisingConcerns.module.scss';
import cn from 'classnames';

interface DynamicActionRaisingConcernsProps {
  actionDetails: AdcmDynamicActionDetails;
  onNext: (changes: Partial<AdcmDynamicActionRunConfig>) => void;
  onCancel: () => void;
}

const DynamicActionRaisingConcerns = ({ onNext, onCancel }: DynamicActionRaisingConcernsProps) => {
  const [isRaiseNonBlockingConcerns, setIsRaiseNonBlockingConcerns] = useState(false);

  const handleNext = () => {
    onNext({ shouldBlockObject: !isRaiseNonBlockingConcerns });
  };

  const handleRaiseConcernsChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setIsRaiseNonBlockingConcerns(event.target.checked);
  };

  return (
    <div className={s.dynamicActionRaisingConcerns}>
      <div className={s.dynamicActionRaisingConcerns__body}>
        <Switch
          label="Raise non-blocking concern"
          isToggled={isRaiseNonBlockingConcerns}
          onChange={handleRaiseConcernsChange}
        />
        {isRaiseNonBlockingConcerns && (
          <WarningMessage>
            Please note that the <strong>Disable object blocking after action runs</strong> feature allows users to run{' '}
            parallel processes on an object and its children and parents. This feature is intended for experienced users
            who are familiar with the potential risks and implications associated with the managed environments.
          </WarningMessage>
        )}
      </div>
      <div className={cn(dialogStyles.dynamicActionDialog__footer, s.dynamicActionRaisingConcerns__footer)}>
        <ButtonGroup>
          <Button variant="secondary" onClick={onCancel}>
            Cancel
          </Button>
          <Button onClick={handleNext}>Next</Button>
        </ButtonGroup>
      </div>
    </div>
  );
};

export default DynamicActionRaisingConcerns;
