import type React from 'react';
import { useMemo } from 'react';
import { useState } from 'react';
import Checkbox from '@uikit/Checkbox/Checkbox';
import { Input, Switch, WarningMessage } from '@uikit';
import { useStore } from '@hooks';
import s from './ActionWizardLastStage.module.scss';
import { useActionWizardLastStageContext } from '@uikit/ActionWizardSteps/ActionWizardLastStage/ActionWizardLastStageContextProvider/ActionWizardLastStageContext.context';

const ActionWizardLastStage: React.FC = () => {
  const actionDetails = useStore((s) => s.adcm.clustersDynamicActions.dialog.actionDetails);
  const [isRaiseNonBlockingConcerns, setIsRaiseNonBlockingConcerns] = useState(false);
  const { formData, onChange } = useActionWizardLastStageContext();

  const disclaimerText = useMemo(() => {
    if (actionDetails?.disclaimer && actionDetails.disclaimer !== '') {
      return actionDetails.disclaimer;
    }
    return `${actionDetails?.displayName} will be started.`;
  }, [actionDetails]);

  const handleRaiseConcernsChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const isEnabled = event.target.checked;
    setIsRaiseNonBlockingConcerns(isEnabled);
    onChange({ shouldBlockObject: !isEnabled });
  };

  const handleVerboseChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChange({ isVerbose: event.target.checked });
  };

  const handleDescriptionChange = (event: React.ChangeEvent<HTMLInputElement>) => {
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

      <div>{disclaimerText}</div>

      <span>You can add short description for performed job. But it's not required.</span>

      <Input
        value={formData.description}
        type="text"
        onChange={handleDescriptionChange}
        placeholder="Running a performance check with new parameters. Comparing results with and without cache, focusing on anomalies and overall behavior."
        autoComplete="off"
      />

      <Checkbox checked={formData.isVerbose} label="Verbose" onChange={handleVerboseChange} />
    </div>
  );
};

export default ActionWizardLastStage;
