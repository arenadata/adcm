import { useDialogContext } from '@uikit/DialogV2/Dialog.context';
import s from './ActionWizardConflictProcessDialog.module.scss';
import { Button, ButtonGroup } from '@uikit';

interface ActionWizardConflictProcessDialogControlsProps {
  onCancel: () => void;
  onContinue: () => void;
  onStartNew: () => void;
}

const ActionWizardConflictProcessDialogControls = ({
  onCancel,
  onContinue,
  onStartNew,
}: ActionWizardConflictProcessDialogControlsProps) => {
  const { isActionDisabled, buttonInControlWithFocus } = useDialogContext();

  return (
    <ButtonGroup className={s.actionWizardConflictProcessDialogControls__customControl} data-test="dialog-control">
      <Button
        //
        variant="secondary"
        onClick={onCancel}
        tabIndex={buttonInControlWithFocus === 'cancel' ? 1 : 0}
        data-test="btn-reject"
      >
        Exit
      </Button>
      <Button variant="secondary" onClick={onContinue}>
        Continue
      </Button>
      <Button
        disabled={isActionDisabled}
        onClick={onStartNew}
        data-test="btn-accept"
        autoFocus={buttonInControlWithFocus === 'action'}
      >
        Start new
      </Button>
    </ButtonGroup>
  );
};

export default ActionWizardConflictProcessDialogControls;
