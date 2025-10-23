import { Button, ButtonGroup, Checkbox, MultilineInput } from '@uikit';
import type { AdcmDynamicActionDetails, AdcmDynamicActionRunConfig } from '@models/adcm';
import dialogStyles from '../../DynamicActionDialog.module.scss';
import s from './DynamicActionConfirm.module.scss';
import cn from 'classnames';

interface DynamicActionConfirmProps {
  actionDetails: AdcmDynamicActionDetails;
  onRun: (changes: Partial<AdcmDynamicActionRunConfig>) => void;
  onCancel: () => void;
  onStateChange: (data: Partial<AdcmDynamicActionRunConfig>) => void;
  isVerbose: boolean;
  description?: string;
}

const DynamicActionConfirm = ({
  onRun,
  onCancel,
  actionDetails,
  onStateChange,
  description = '',
  isVerbose,
}: DynamicActionConfirmProps) => {
  const handleRun = () => {
    onRun({ isVerbose, description });
  };

  const handleVerboseChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onStateChange({ isVerbose: event.target.checked });
  };

  const handleDescriptionChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    onStateChange({ description: event.target.value });
  };

  return (
    <div className={s.dynamicActionConfirm}>
      <div>{actionDetails.disclaimer || `${actionDetails.displayName} will be started.`}</div>
      <div className={s.dynamicActionConfirm__message}>
        You can add short description for performed job. But it's not required
      </div>
      <MultilineInput
        className={s.dynamicActionConfirm__input}
        value={description}
        onChange={handleDescriptionChange}
        maxLength={255}
      />
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
