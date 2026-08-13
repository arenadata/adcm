import { useCallback, useMemo } from 'react';
import type { CSSProperties } from 'react';
import type { ConfigurationField, ConfigurationNodeView } from '../../ConfigurationEditor.types';
import type { ChangeConfigurationNodeValueHandler } from '../ConfigurationTree.types';
import type { JSONPrimitive } from '@models/json';
import { getInlineValueStyle } from '../../InlinePrimitiveFieldControl/InlineAutoSize.utils';
import { getInlinePrimitiveFieldControlType } from '../../InlinePrimitiveFieldControl/InlinePrimitiveFieldControl.utils';

interface UseInlineFieldParams {
  node: ConfigurationNodeView;
  fieldNodeData: ConfigurationField;
  onChange: ChangeConfigurationNodeValueHandler;
}

export interface UseInlineFieldResult {
  isEditable: boolean;
  showInlineControl: boolean;
  isStringField: boolean;
  valueStyle: CSSProperties | undefined;
  onChange: (value: JSONPrimitive) => void;
  onValueClick: (event: React.MouseEvent<HTMLDivElement>) => void;
}

export const useInlineField = ({ node, fieldNodeData, onChange }: UseInlineFieldParams): UseInlineFieldResult => {
  const inlineControlType = getInlinePrimitiveFieldControlType(fieldNodeData.fieldSchema);
  const isInlineField = inlineControlType !== null;
  const isEditable = isInlineField && !fieldNodeData.isReadonly;
  const showInlineControl = isEditable || inlineControlType === 'boolean';
  const isStringField = inlineControlType === 'string';
  const isNumberField = inlineControlType === 'number';

  const valueStyle = useMemo(
    () =>
      getInlineValueStyle({
        isInlineNumberField: isNumberField,
        value: fieldNodeData.value,
      }),
    [fieldNodeData.value, isNumberField],
  );

  const handleChange = useCallback(
    (nextValue: JSONPrimitive) => {
      onChange(node, nextValue);
    },
    [node, onChange],
  );

  const handleValueClick = useCallback((event: React.MouseEvent<HTMLDivElement>) => {
    event.stopPropagation();
  }, []);

  return {
    isEditable,
    showInlineControl,
    isStringField,
    valueStyle,
    onChange: handleChange,
    onValueClick: handleValueClick,
  };
};
