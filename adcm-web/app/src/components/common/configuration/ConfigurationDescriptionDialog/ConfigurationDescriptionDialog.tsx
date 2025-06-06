import type React from 'react';
import { useEffect, useState } from 'react';
import { DialogV2, Input } from '@uikit';

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

  if (!isOpen) return null;

  return (
    <DialogV2 title="Configuration description" actionButtonLabel="Create" onAction={handleSave} onCancel={onCancel}>
      <p>You can add short description for this config version. But it's not required</p>
      <Input value={description} onChange={handleChange} placeholder="Configuration description..." />
    </DialogV2>
  );
};

export default ConfigurationDescriptionDialog;
