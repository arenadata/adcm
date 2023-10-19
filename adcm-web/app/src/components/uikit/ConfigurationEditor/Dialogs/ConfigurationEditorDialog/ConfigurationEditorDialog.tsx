import Modal from '@uikit/Modal/Modal';
import { Button } from '@uikit';
import s from './ConfigurationEditorDialog.module.scss';

export interface ConfigurationEditorDialogProps extends React.PropsWithChildren {
  triggerRef: React.RefObject<HTMLElement>;
  isOpen: boolean;
  width?: string;
  maxWidth?: string;
  onOpenChange: (isOpen: boolean) => void;
  onCancel: () => void;
  onApply: () => void;
}

const ConfigurationEditorDialog = ({
  isOpen,
  children,
  width = '640px',
  maxWidth = '100%',
  onOpenChange,
  onCancel,
  onApply,
}: ConfigurationEditorDialogProps) => {
  return (
    <Modal isOpen={isOpen} onOpenChange={onOpenChange} style={{ width, maxWidth }}>
      <div className={s.configurationEditorDialog}>
        <div className={s.configurationEditorDialog__body}>{children}</div>
        <div className={s.configurationEditorDialog__footer}>
          <Button variant="secondary" onClick={onCancel}>
            Cancel
          </Button>
          <Button onClick={onApply}>Apply</Button>
        </div>
      </div>
    </Modal>
  );
};

export default ConfigurationEditorDialog;
