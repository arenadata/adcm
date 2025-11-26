import IconButton from '@uikit/IconButton/IconButton';
import Popover from '@uikit/Popover/Popover';
import PopoverPanelDefault from '@uikit/Popover/PopoverPanelDefault/PopoverPanelDefault';
import { useRef, useState } from 'react';
import { discriminatorFieldName } from '../../ConfigurationTree.constants';
import type { ConfigurationSelectableObject } from '@uikit/ConfigurationEditor/ConfigurationEditor.types';
import type { JSONObject } from '@models/json';
import s from './ObjectSchemaSelect.module.scss';
import cn from 'classnames';

export interface ObjectSchemaSelectProps {
  data: ConfigurationSelectableObject;
  onChange: (selection: string) => void;
}

const ObjectSchemaSelect = ({ data, onChange }: ObjectSchemaSelectProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const iconRef = useRef<HTMLButtonElement>(null);

  const options = (data.fieldSchema.oneOf ?? []).map((schema) => {
    const discriminatorField = schema?.properties?.[discriminatorFieldName];
    const value = discriminatorField?.title ?? (discriminatorField?.const as string) ?? '';
    const label = discriminatorField?.title ?? (value as string);

    return { value, label };
  });

  const handleOptionClick = (e: React.MouseEvent<HTMLLIElement>) => {
    const selection = e.currentTarget.dataset.selection;
    if (selection) {
      onChange(selection);
      setIsOpen(false);
    }
  };

  const handleIconClick = () => {
    setIsOpen((prev) => !prev);
  };

  const discriminatorValue =
    data.value === null ? null : ((data.value as JSONObject)[discriminatorFieldName] as string);

  const iconClassName = cn(s.objectSchemaSelect__icon, {
    [s.objectSchemaSelect__icon_expanded]: isOpen,
  });

  return (
    <>
      {discriminatorValue}
      <div className={s.objectSchemaSelect}>
        <IconButton ref={iconRef} size={12} icon="chevron" className={iconClassName} onClick={handleIconClick} />
        <Popover isOpen={isOpen} onOpenChange={setIsOpen} triggerRef={iconRef} placement="bottom-start" offset={8}>
          <PopoverPanelDefault className={s.objectSchemaSelect__selectPanel}>
            <ul>
              {options.map((option) => (
                <li
                  key={option.label}
                  className={s.objectSchemaSelect__option}
                  data-selection={option.value}
                  onClick={handleOptionClick}
                >
                  {option.label}
                </li>
              ))}
            </ul>
          </PopoverPanelDefault>
        </Popover>
      </div>
    </>
  );
};

export default ObjectSchemaSelect;
