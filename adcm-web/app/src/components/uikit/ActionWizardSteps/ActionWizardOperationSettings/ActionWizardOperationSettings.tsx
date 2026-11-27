import { useRef, useState } from 'react';
import FlexGroup from '@uikit/FlexGroup/FlexGroup';
import Icon from '@uikit/Icon/Icon';
import IconButton from '@uikit/IconButton/IconButton';
import Popover from '@uikit/Popover/Popover';
import PopoverPanelDefault from '@uikit/Popover/PopoverPanelDefault/PopoverPanelDefault';
import Switch from '@uikit/Switch/Switch';
import Tooltip from '@uikit/Tooltip/Tooltip';
import type { AdcmWizardOperationSettings } from '@models/adcm/wizard';
import { operationSettingItems } from './ActionWizardOperationSettings.constants';
import s from './ActionWizardOperationSettings.module.scss';

interface ActionWizardOperationSettingsProps {
  settings: AdcmWizardOperationSettings;
  isDisabled: boolean;
  onChange: (settings: AdcmWizardOperationSettings) => void;
}

const ActionWizardOperationSettings = ({ settings, isDisabled, onChange }: ActionWizardOperationSettingsProps) => {
  const triggerRef = useRef<HTMLButtonElement>(null);
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <IconButton ref={triggerRef} icon="g1-config" variant="secondary" onClick={() => setIsOpen((prev) => !prev)} />
      <Popover isOpen={isOpen} onOpenChange={setIsOpen} triggerRef={triggerRef} placement="bottom-end">
        <PopoverPanelDefault className={s.operationSettings}>
          {operationSettingItems.map(({ key, label, hint }) => (
            <FlexGroup key={key} gap="8px">
              <Switch
                label={label}
                isToggled={settings[key]}
                disabled={isDisabled}
                onChange={(event) => onChange({ ...settings, [key]: event.target.checked })}
              />
              <Tooltip label={hint} placement="top" className={s.operationSettings__hint}>
                <Icon name="g1-info" size={16} className={s.operationSettings__hintIcon} />
              </Tooltip>
            </FlexGroup>
          ))}
        </PopoverPanelDefault>
      </Popover>
    </>
  );
};

export default ActionWizardOperationSettings;
