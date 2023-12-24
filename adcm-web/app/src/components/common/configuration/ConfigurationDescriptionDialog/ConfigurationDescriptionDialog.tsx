import React, { useEffect, useState } from 'react';
import { Dialog, Input } from '@uikit';

interface ConfigurationDescriptionDialogProps {
  isOpen: boolean;
  onCancel: () => void;
  onSave: (description: string) => void;
}

const ConfigurationDescriptionDialog: React.FC<ConfigurationDescriptionDialogProps> = ({
  isOpen,
  onCancel,
  onSave,
}) => {
  const [description, setDescription] = useState('');
  useEffect(() => {
    if (!isOpen) {
      setDescription('');
    }
  }, [isOpen]);

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setDescription(event.target.value);
  };
  const handleSave = () => {
    onSave(description);
    onCancel();
  };

  return (
    <Dialog
      title="Configuration description"
      isOpen={isOpen}
      onOpenChange={onCancel}
      actionButtonLabel="Create"
      onAction={handleSave}
    >
      <p>You can add short description for this config version. But it's not required</p>
      <Input value={description} onChange={handleChange} placeholder="Configuration description..." />
    </Dialog>
  );
};

export default ConfigurationDescriptionDialog;
