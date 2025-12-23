import type React from 'react';
import { useMemo } from 'react';
import Checkbox from '@uikit/Checkbox/Checkbox';
import { MultilineInput, Switch, WarningMessage } from '@uikit';
import { useStore } from '@hooks';
import s from './ActionWizardLastStage.module.scss';
import { useActionWizardLastStageContext } from '@uikit/ActionWizardSteps/ActionWizardLastStage/ActionWizardLastStageContextProvider/ActionWizardLastStageContext.context';

const ActionWizardLastStage: React.FC = () => {
  const actionDetails = useStore((s) => s.adcm.clustersDynamicActions.dialog.actionDetails);
  const { formData, onChange } = useActionWizardLastStageContext();
  const isRaiseNonBlockingConcerns = !formData.shouldBlockObject;

  const disclaimerText = useMemo(() => {
    if (actionDetails?.disclaimer && actionDetails.disclaimer !== '') {
      return actionDetails.disclaimer;
    }
    return `${actionDetails?.displayName} will be started.`;
  }, [actionDetails]);

  const handleRaiseConcernsChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChange({ shouldBlockObject: !event.target.checked });
  };

  const handleVerboseChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChange({ isVerbose: event.target.checked });
  };

  const handleDescriptionChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    onChange({ description: event.target.value });
  };

  return (
    <div className={s.actionWizardLastStage__wrapper}>
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

      <div className={s.actionWizardLastStage__disclaimerText}>{disclaimerText}</div>

      <div className={s.actionWizardLastStage__descriptionWrapper}>
        <span className={s.actionWizardLastStage__descriptionLabel}>
          You can add short description for performed job. But it's not required.
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

      <Checkbox checked={formData.isVerbose} label="Verbose" onChange={handleVerboseChange} />
    </div>
  );
};

export default ActionWizardLastStage;
