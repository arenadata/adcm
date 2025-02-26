import { useState } from 'react';
import Switch from '@uikit/Switch/Switch';
import Button from '@uikit/Button/Button';
import { useAdcmFieldAttributesContext } from './AdcmFieldAttributes.context';
import s from './AdcmFieldAttributesWidgetContent.module.scss';

const AdcmFieldAttributesWidgetContent = () => {
  const { path, attributes, onFieldAttributesChange, onCancel } = useAdcmFieldAttributesContext();
  const [localAttributes, setLocalAttributes] = useState(attributes);

  const handleApply = () => {
    onFieldAttributesChange(path, localAttributes);
  };

  const handleIsActiveChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setLocalAttributes({ ...localAttributes, isActive: e.target.checked });
  };

  const handleIsSyncedChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setLocalAttributes({ ...localAttributes, isSynchronized: e.target.checked });
  };

  return (
    <div className={s.adcmFieldAttributesWidgetContent}>
      {localAttributes.isActive !== undefined && (
        <Switch size="small" label="Is Active" isToggled={localAttributes.isActive} onChange={handleIsActiveChange} />
      )}
      {localAttributes.isSynchronized !== undefined && (
        <Switch
          size="small"
          label="Is Synced"
          isToggled={localAttributes.isSynchronized}
          onChange={handleIsSyncedChange}
        />
      )}
      <div className={s.buttons}>
        <Button variant="secondary" onClick={onCancel}>
          Close
        </Button>
        <Button onClick={handleApply}>Apply</Button>
      </div>
    </div>
  );
};

export default AdcmFieldAttributesWidgetContent;
