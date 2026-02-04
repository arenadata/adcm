import { discriminatorFieldName, nullStub } from '../../ConfigurationTree.constants';
import type { ConfigurationSelectableObject } from '@uikit/ConfigurationEditor/ConfigurationEditor.types';
import { isValueSet, type JSONObject } from '@models/json';
import s from './ObjectSchemaSelect.module.scss';
import treeStyles from '../../ConfigurationTree.module.scss';
import ActionMenu from '@uikit/ActionMenu/ActionMenu.tsx';
import Icon from '@uikit/Icon/Icon.tsx';
import { useMemo, useRef } from 'react';

export interface ObjectSchemaSelectProps {
  data: ConfigurationSelectableObject;
  onChange: (selection: string) => void;
}

const ObjectSchemaSelect = ({ data, onChange }: ObjectSchemaSelectProps) => {
  const optionsMap = useRef<Map<string, string>>(new Map<string, string>());

  const options = useMemo(
    () =>
      (data.fieldSchema.oneOf ?? []).map((schema) => {
        const discriminatorField = schema?.properties?.[discriminatorFieldName];

        const value = (discriminatorField?.const as string) || '';
        const label = schema?.properties?.[value]?.title ?? value;
        optionsMap.current.set(value, label);

        return { value, label };
      }),
    [data.fieldSchema.oneOf],
  );

  const handleChange = (selection: string | null) => {
    if (selection) {
      onChange(selection);
    }
  };

  const selectDisabled = data.isReadonly || !(data.fieldSchema.adcmMeta?.synchronization?.isAllowChange ?? true);

  const discriminatorLabelEl = getNodeSelectedLabelEl(data, optionsMap.current);

  return (
    <ActionMenu placement="bottom-start" value={null} options={options} onChange={handleChange}>
      <button className={s.objectSchemaSelect} disabled={selectDisabled}>
        {discriminatorLabelEl}
        <Icon name="chevron" size={12} className={s.objectSchemaSelect__icon} />
      </button>
    </ActionMenu>
  );
};

export default ObjectSchemaSelect;

const getNodeSelectedLabelEl = (data: ConfigurationSelectableObject, optionsMap: Map<string, string>) => {
  const discriminatorValue = !isValueSet(data.value)
    ? null
    : ((data.value as JSONObject)[discriminatorFieldName] as string);

  const discriminatorLabel = discriminatorValue ? optionsMap.get(discriminatorValue) : nullStub;

  return (
    <span className={treeStyles.nodeContent__value} data-test={discriminatorLabel ? undefined : 'null-stub'}>
      {discriminatorLabel}
    </span>
  );
};
