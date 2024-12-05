import type React from 'react';
import { useState } from 'react';
import ConfigurationToolbar from '../ConfigurationToolbar/ConfigurationToolbar';
import ConfigurationDescriptionDialog from '../ConfigurationDescriptionDialog/ConfigurationDescriptionDialog';

interface ConfigurationSubHeaderProps {
  onSave: (description: string) => void;
  onRevert: () => void;
  isViewDraft: boolean;
}

const ConfigurationSubHeader: React.FC<ConfigurationSubHeaderProps> = ({ onSave, ...props }) => {
  const [isOpenDescriptionDialog, setIsOpenDescriptionDialog] = useState(false);

  const openDescriptionDialog = () => {
    setIsOpenDescriptionDialog(true);
  };
  const closeDescriptionDialog = () => {
    setIsOpenDescriptionDialog(false);
  };

  return (
    <>
      <ConfigurationDescriptionDialog
        isOpen={isOpenDescriptionDialog}
        onCancel={closeDescriptionDialog}
        onSave={onSave}
      />
      <ConfigurationToolbar onSave={openDescriptionDialog} {...props} />
    </>
  );
};

export default ConfigurationSubHeader;
