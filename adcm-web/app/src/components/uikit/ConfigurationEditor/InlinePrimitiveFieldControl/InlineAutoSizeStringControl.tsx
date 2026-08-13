import { useCallback, useEffect, useRef, useState } from 'react';
import cn from 'classnames';
import type { JSONPrimitive } from '@models/json';
import {
  getInlineStringDisplayText,
  getInlineStringEditValue,
  isInlineStringDisplayStub,
} from './InlineAutoSize.utils';
import s from './InlinePrimitiveFieldControl.module.scss';

export interface InlineAutoSizeStringControlProps {
  className: string;
  value: JSONPrimitive;
  isReadonly?: boolean;
  autoFocus?: boolean;
  onChange: (value: string) => void;
}

const InlineAutoSizeStringControl = ({
  className,
  value,
  isReadonly = false,
  autoFocus = false,
  onChange,
}: InlineAutoSizeStringControlProps) => {
  const [isFocused, setIsFocused] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const fieldClassName = cn(className, s.autoSizeField, s.autoSizeField_string);
  const displayText = getInlineStringDisplayText(value);
  const isStub = isInlineStringDisplayStub(value);
  const editValue = getInlineStringEditValue(value);

  const handleValueChange = useCallback(
    (nextValue: string) => {
      onChange(nextValue);
    },
    [onChange],
  );

  const handleTextareaChange = useCallback(
    (event: React.ChangeEvent<HTMLTextAreaElement>) => {
      handleValueChange(event.target.value);
    },
    [handleValueChange],
  );

  const handleTextareaFocus = useCallback(() => {
    setIsFocused(true);
  }, []);

  const handleTextareaBlur = useCallback(() => {
    setIsFocused(false);
  }, []);

  const handleDisplayMouseDown = useCallback((event: React.MouseEvent<HTMLDivElement>) => {
    event.preventDefault();
    textareaRef.current?.focus();
  }, []);

  useEffect(() => {
    if (!autoFocus || isReadonly) {
      return;
    }

    setIsFocused(true);
    const frameId = requestAnimationFrame(() => {
      textareaRef.current?.focus();
    });

    return () => cancelAnimationFrame(frameId);
  }, [autoFocus, isReadonly]);

  return (
    <div className={fieldClassName}>
      {!isFocused && (
        <div
          className={cn(s.autoSizeField__display, { [s.autoSizeField__display_stub]: isStub })}
          title={displayText}
          onMouseDown={handleDisplayMouseDown}
        >
          {displayText}
        </div>
      )}
      <textarea
        ref={textareaRef}
        className={cn(s.autoSizeField__textarea, {
          [s.autoSizeField__textarea_hidden]: !isFocused,
        })}
        value={editValue}
        readOnly={isReadonly}
        onChange={handleTextareaChange}
        onFocus={handleTextareaFocus}
        onBlur={handleTextareaBlur}
      />
    </div>
  );
};

export default InlineAutoSizeStringControl;
