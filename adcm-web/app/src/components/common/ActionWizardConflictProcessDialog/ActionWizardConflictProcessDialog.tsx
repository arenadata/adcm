import { DialogV2 } from '@uikit';
import ActionWizardConflictProcessDialogControls from '@commonComponents/ActionWizardConflictProcessDialog/ActionWizardConflictProcessDialogControls';

interface ActionWizardConflictProcessDialogProps {
  title: string;
  description: string;
  onCancel: () => void;
  onContinue: () => void;
  onStartNew: () => void;
}

const ActionWizardConflictProcessDialog = ({
  title,
  description,
  onCancel,
  onContinue,
  onStartNew,
}: ActionWizardConflictProcessDialogProps) => {
  return (
    <DialogV2
      title={title}
      dialogControls={
        <ActionWizardConflictProcessDialogControls
          onCancel={onCancel}
          onContinue={onContinue}
          onStartNew={onStartNew}
        />
      }
      onCancel={onCancel}
    >
      {description}
    </DialogV2>
  );
};
export default ActionWizardConflictProcessDialog;
