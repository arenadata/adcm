import { useCallback, useMemo } from 'react';
import cn from 'classnames';
import type { SchemaDefinition } from '@models/adcm';
import type { JSONPrimitive } from '@models/json';
import Select from '@uikit/Select/SingleSelect/Select/Select';
import Checkbox from '@uikit/Checkbox/Checkbox';
import InputNumber from '@uikit/InputNumber/InputNumber';
import { getEnumOptions } from '../Dialogs/FieldControls/EnumControl.utils';
import { nullStub } from '../ConfigurationTree/ConfigurationTree.constants';
import { getInlinePrimitiveFieldControlType } from './InlinePrimitiveFieldControl.utils';
import { INLINE_ENUM_PLACEHOLDER } from './InlineAutoSize.utils';
import InlineAutoSizeStringControl from './InlineAutoSizeStringControl';
import s from './InlinePrimitiveFieldControl.module.scss';

export interface InlinePrimitiveFieldControlProps {
  fieldSchema: SchemaDefinition;
  value: JSONPrimitive;
  isReadonly?: boolean;
  autoFocus?: boolean;
  onChange: (value: JSONPrimitive) => void;
}

const InlinePrimitiveFieldControl = ({
  fieldSchema,
  value,
  isReadonly = false,
  autoFocus = false,
  onChange,
}: InlinePrimitiveFieldControlProps) => {
  const controlType = getInlinePrimitiveFieldControlType(fieldSchema);

  const handleStringChange = useCallback(
    (nextValue: string) => {
      onChange(nextValue);
    },
    [onChange],
  );

  const handleNumberChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      if (event.target.value === '') {
        onChange(null);
        return;
      }

      onChange(event.target.valueAsNumber);
    },
    [onChange],
  );

  const handleBooleanChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      onChange(event.target.checked);
    },
    [onChange],
  );

  const handleEnumChange = useCallback(
    (nextValue: unknown) => {
      onChange(nextValue as JSONPrimitive);
    },
    [onChange],
  );

  const enumOptions = useMemo(() => getEnumOptions(fieldSchema), [fieldSchema]);

  if (controlType === null) {
    return null;
  }

  switch (controlType) {
    case 'string': {
      return (
        <InlineAutoSizeStringControl
          className={s.embeddedField}
          value={value}
          isReadonly={isReadonly}
          autoFocus={autoFocus}
          suggestions={fieldSchema.adcmMeta?.stringExtra?.suggestions}
          onChange={handleStringChange}
        />
      );
    }
    case 'number': {
      return (
        <InputNumber
          className={cn(s.embeddedField, s.autoSizeField, s.autoSizeField_number)}
          value={(value as number) ?? ''}
          readOnly={isReadonly}
          min={fieldSchema.minimum}
          max={fieldSchema.maximum}
          placeholder={nullStub}
          autoFocus={autoFocus}
          onChange={handleNumberChange}
        />
      );
    }
    case 'boolean': {
      return (
        <Checkbox
          className={s.checkbox}
          checked={Boolean(value)}
          readOnly={isReadonly}
          autoFocus={autoFocus}
          onChange={handleBooleanChange}
        />
      );
    }
    case 'enum': {
      const enumClassName = cn(s.embeddedField, s.autoSizeField, s.autoSizeField_select);

      return (
        <Select
          className={enumClassName}
          value={value}
          onChange={handleEnumChange}
          options={enumOptions}
          isSearchable={false}
          placeholder={INLINE_ENUM_PLACEHOLDER}
          disabled={isReadonly}
          autoFocus={autoFocus}
        />
      );
    }
    default: {
      return null;
    }
  }
};

export default InlinePrimitiveFieldControl;
