import Modal from '@uikit/Modal/Modal';
import IconButton from '@uikit/IconButton/IconButton';
import s from './ConfigurationEditorDialog.module.scss';

export interface ConfigurationEditorDialogProps extends React.PropsWithChildren {
  triggerRef: React.RefObject<HTMLElement>;
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
}

const ConfigurationEditorDialog = ({ isOpen, children, onOpenChange }: ConfigurationEditorDialogProps) => {
  const handleIconClick = () => {
    onOpenChange(false);
  };

  return (
    <Modal isOpen={isOpen} onOpenChange={onOpenChange}>
      <div className={s.configurationEditorDialog} style={{ width: '640px' }}>
        <IconButton
          icon="g2-close"
          variant="secondary"
          size={28}
          className={s.configurationEditorDialog__close}
          onClick={handleIconClick}
          title="Close"
        />
        <div className={s.configurationEditorDialog__body}>{children}</div>
      </div>
    </Modal>
  );
};

export default ConfigurationEditorDialog;
