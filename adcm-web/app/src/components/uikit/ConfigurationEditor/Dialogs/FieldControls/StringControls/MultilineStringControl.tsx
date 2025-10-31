import { useMemo, useState } from 'react';
import CodeEditor from '@uikit/CodeEditor/CodeEditor';
import ConfigurationField from '../ConfigurationField';
import type { SingleSchemaDefinition } from '@models/adcm';
import type { JSONPrimitive } from '@models/json';
import { prettifyJson } from '@utils/stringUtils';
import { validate } from './StringControls.utils';

const textTransformers: { [format: string]: (value: string) => string } = {
  json: prettifyJson,
};

interface MultilineStringControlProps {
  fieldName: string;
  value: JSONPrimitive;
  defaultValue: JSONPrimitive;
  fieldSchema: SingleSchemaDefinition;
  isReadonly: boolean;
  onChange: (newValue: JSONPrimitive, isValid?: boolean) => void;
  onApply: () => void;
}

const MultilineStringControl = ({
  fieldName,
  value,
  fieldSchema,
  defaultValue,
  isReadonly,
  onChange,
  onApply,
}: MultilineStringControlProps) => {
  const stringValue = value?.toString() ?? '';
  const format = fieldSchema.format ?? 'text';
  const [isFormatted, setIsFormatted] = useState(false);
  const [error, setError] = useState<string | undefined>(undefined);

  const code = useMemo(() => {
    if (!isFormatted) {
      const transformer = textTransformers[format];
      if (transformer) {
        setIsFormatted(true);
        return transformer(stringValue);
      }
    }

    return stringValue;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stringValue]);

  const handleChange = (code: string) => {
    const error = validate(code, fieldSchema);
    setError(error);
    onChange(code, error === undefined);
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.code === 'Enter' && event.ctrlKey) {
      onApply();
    }
  };

  return (
    <ConfigurationField
      label={fieldName}
      fieldSchema={fieldSchema}
      defaultValue={defaultValue}
      disabled={isReadonly}
      error={error}
      onResetToDefault={onChange}
    >
      <CodeEditor
        isSecret={fieldSchema.adcmMeta.isSecret}
        language={format}
        code={code}
        isReadonly={isReadonly}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
      />
    </ConfigurationField>
  );
};

export default MultilineStringControl;
