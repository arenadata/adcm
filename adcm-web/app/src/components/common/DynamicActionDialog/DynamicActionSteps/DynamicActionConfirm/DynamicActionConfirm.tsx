import { useState } from 'react';
import { Button, ButtonGroup, Checkbox } from '@uikit';
import type { AdcmDynamicActionDetails, AdcmDynamicActionRunConfig } from '@models/adcm';
import dialogStyles from '../../DynamicActionDialog.module.scss';
import s from './DynamicActionConfirm.module.scss';
import cn from 'classnames';

interface DynamicActionConfirmProps {
  actionDetails: AdcmDynamicActionDetails;
  onRun: (changes: Partial<AdcmDynamicActionRunConfig>) => void;
  onCancel: () => void;
}

const DynamicActionConfirm = ({ actionDetails, onRun, onCancel }: DynamicActionConfirmProps) => {
  const [isVerbose, setIsVerbose] = useState(false);

  const handleRun = () => {
    onRun({ isVerbose });
  };

  const handleVerboseChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setIsVerbose(event.target.checked);
  };

  return (
    <div className={s.dynamicActionConfirm}>
      <div>{actionDetails.disclaimer || `${actionDetails.displayName} will be started.`}</div>
      <div className={cn(dialogStyles.dynamicActionDialog__footer, s.dynamicActionConfirm__footer)}>
        <Checkbox checked={isVerbose} label="Verbose" onChange={handleVerboseChange} />
        <ButtonGroup>
          <Button variant="secondary" onClick={onCancel}>
            Cancel
          </Button>
          <Button onClick={handleRun}>Run</Button>
        </ButtonGroup>
      </div>
    </div>
  );
};

export default DynamicActionConfirm;
