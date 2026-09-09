import type React from 'react';
import { MultilineInput, Switch, WarningMessage } from '@uikit';
import s from './ActionWizardLastStage.module.scss';
import { useActionWizardLastStageContext } from '@uikit/ActionWizardSteps/ActionWizardLastStage/ActionWizardLastStageContextProvider/ActionWizardLastStageContext.context';
import type { AdcmDynamicActionDetails } from '@models/adcm';

interface ActionWizardLastStageProps {
  actionDetails: AdcmDynamicActionDetails | null;
}

const ActionWizardLastStage: React.FC<ActionWizardLastStageProps> = ({ actionDetails }) => {
  const { formData, onChange } = useActionWizardLastStageContext();

  const handleRaiseConcernsChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChange({ shouldBlockObject: event.target.checked });
  };

  const handleVerboseChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChange({ isVerbose: event.target.checked });
  };

  const handleDescriptionChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    onChange({ description: event.target.value });
  };

  return (
    <div className={s.actionWizardLastStage__wrapper}>
      {actionDetails?.disclaimer && (
        <div className={s.actionWizardLastStage__disclaimerText}>{actionDetails.disclaimer}</div>
      )}

      <div className={s.actionWizardLastStage__descriptionWrapper}>
        <span className={s.actionWizardLastStage__descriptionLabel}>
          You can add short description for performed job. But it&apos;s not required
        </span>

        <MultilineInput
          title="You can add short description for performed job. But it's not required."
          className={s.actionWizardLastStage__descriptionValue}
          value={formData.description}
          type="text"
          onChange={handleDescriptionChange}
          autoComplete="off"
          maxLength={255}
        />
      </div>

      <div className={s.actionWizardLastStage__switches}>
        <Switch
          label="Raise blocking concern"
          isToggled={formData.shouldBlockObject}
          onChange={handleRaiseConcernsChange}
        />
        {!formData.shouldBlockObject && (
          <WarningMessage>
            Please note that the Disable object blocking after action runs feature allows users to run parallel
            processes on an object and its children and parents. This feature is intended for experienced users who are
            familiar with the potential risks and implications associated with the managed environments.
          </WarningMessage>
        )}
        <div className={s.actionWizardLastStage__verbose}>
          <Switch id="action-wizard-verbose" isToggled={formData.isVerbose} onChange={handleVerboseChange} />
          <div className={s.actionWizardLastStage__verboseText}>
            <label htmlFor="action-wizard-verbose">Verbose</label>
            <span className={s.actionWizardLastStage__verboseHint}>
              Shows detailed debug output. May slow down execution.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ActionWizardLastStage;
