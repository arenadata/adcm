import { Button, ButtonGroup, MultilineInput, Switch, WarningMessage } from '@uikit';
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
  shouldBlockObject: boolean;
  isConcernControlShown?: boolean;
}

const DynamicActionConfirm = ({
  onRun,
  onCancel,
  actionDetails,
  onStateChange,
  description = '',
  isVerbose,
  shouldBlockObject,
  isConcernControlShown = true,
}: DynamicActionConfirmProps) => {
  const handleRun = () => {
    onRun({ isVerbose, description, shouldBlockObject });
  };

  const handleVerboseChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onStateChange({ isVerbose: event.target.checked });
  };

  const handleDescriptionChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    onStateChange({ description: event.target.value });
  };

  const handleRaiseConcernsChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onStateChange({ shouldBlockObject: event.target.checked });
  };

  return (
    <div className={s.dynamicActionConfirm}>
      {actionDetails.disclaimer && <div>{actionDetails.disclaimer}</div>}
      <div className={s.dynamicActionConfirm__description}>
        <span className={s.dynamicActionConfirm__message}>
          You can add short description for performed job. But it&apos;s not required
        </span>
        <MultilineInput
          className={s.dynamicActionConfirm__input}
          value={description}
          onChange={handleDescriptionChange}
          maxLength={255}
        />
      </div>
      <div className={s.dynamicActionConfirm__switches}>
        {isConcernControlShown && (
          <>
            <Switch label="Raise blocking concern" isToggled={shouldBlockObject} onChange={handleRaiseConcernsChange} />
            {!shouldBlockObject && (
              <WarningMessage>
                Please note that the Disable object blocking after action runs feature allows users to run parallel
                processes on an object and its children and parents. This feature is intended for experienced users who
                are familiar with the potential risks and implications associated with the managed environments.
              </WarningMessage>
            )}
          </>
        )}
        <div className={s.dynamicActionConfirm__verbose}>
          <Switch id="dynamic-action-verbose" isToggled={isVerbose} onChange={handleVerboseChange} />
          <div className={s.dynamicActionConfirm__verboseText}>
            <label htmlFor="dynamic-action-verbose">Verbose</label>
            <span className={s.dynamicActionConfirm__verboseHint}>
              Shows detailed debug output. May slow down execution.
            </span>
          </div>
        </div>
      </div>
      <div className={cn(dialogStyles.dynamicActionDialog__footer, s.dynamicActionConfirm__footer)}>
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
