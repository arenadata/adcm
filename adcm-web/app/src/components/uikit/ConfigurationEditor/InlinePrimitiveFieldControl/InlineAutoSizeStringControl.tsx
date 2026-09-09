import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import cn from 'classnames';
import type { JSONPrimitive } from '@models/json';
import Popover from '@uikit/Popover/Popover';
import PopoverPanelDefault from '@uikit/Popover/PopoverPanelDefault/PopoverPanelDefault';
import {
  getInlineStringDisplayText,
  getInlineStringEditValue,
  isInlineStringDisplayStub,
} from './InlineAutoSize.utils';
import { filterInlineStringSuggestions } from './InlinePrimitiveFieldControl.utils';
import s from './InlinePrimitiveFieldControl.module.scss';
import suggestionsStyles from '@uikit/InputWithAutocomplete/InputWithAutocomplete.module.scss';
import { EMPTY_ARRAY } from '@constants';

export interface InlineAutoSizeStringControlProps {
  className: string;
  value: JSONPrimitive;
  isReadonly?: boolean;
  autoFocus?: boolean;
  suggestions?: string[];
  onChange: (value: string) => void;
}

const InlineAutoSizeStringControl = ({
  className,
  value,
  isReadonly = false,
  autoFocus = false,
  suggestions,
  onChange,
}: InlineAutoSizeStringControlProps) => {
  const [isFocused, setIsFocused] = useState(false);
  const [isSuggestionsOpen, setIsSuggestionsOpen] = useState(false);
  const fieldRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const fieldClassName = cn(className, s.autoSizeField, s.autoSizeField_string);
  const displayText = getInlineStringDisplayText(value);
  const isStub = isInlineStringDisplayStub(value);
  const editValue = getInlineStringEditValue(value);
  const hasSuggestions = Boolean(suggestions?.length) && !isReadonly;
  const filteredSuggestions = useMemo(
    () => filterInlineStringSuggestions(suggestions ?? EMPTY_ARRAY, editValue),
    [suggestions, editValue],
  );
  const isEditing = isFocused || (isSuggestionsOpen && filteredSuggestions.length > 0);

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
    if (hasSuggestions) {
      setIsSuggestionsOpen(true);
    }
  }, []);

  const handleTextareaBlur = useCallback(() => {
    setIsFocused(false);
  }, []);

  const handleDisplayMouseDown = useCallback((event: React.MouseEvent<HTMLDivElement>) => {
    event.preventDefault();
    textareaRef.current?.focus();
  }, []);

  const handleSelectSuggestion = useCallback(
    (event: React.MouseEvent<HTMLLIElement>) => {
      const nextValue = event.currentTarget.dataset.suggestion;
      if (nextValue === undefined) {
        return;
      }

      handleValueChange(nextValue);
      textareaRef.current?.focus();
    },
    [handleValueChange],
  );

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
    <div ref={fieldRef} className={fieldClassName}>
      {!isEditing && (
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
          [s.autoSizeField__textarea_hidden]: !isEditing,
        })}
        value={editValue}
        readOnly={isReadonly}
        onChange={handleTextareaChange}
        onFocus={handleTextareaFocus}
        onBlur={handleTextareaBlur}
      />
      {hasSuggestions && (
        <Popover
          isOpen={isSuggestionsOpen && filteredSuggestions.length > 0}
          onOpenChange={setIsSuggestionsOpen}
          triggerRef={fieldRef}
          dependencyWidth="min-parent"
          placement="bottom-start"
          offset={8}
          initialFocus={textareaRef}
        >
          <PopoverPanelDefault>
            <ul className={cn(suggestionsStyles.suggestionsList, 'scroll')}>
              {filteredSuggestions.map((suggestion) => (
                <li
                  key={suggestion}
                  className={suggestionsStyles.suggestion}
                  data-suggestion={suggestion}
                  onClick={handleSelectSuggestion}
                >
                  {suggestion}
                </li>
              ))}
            </ul>
          </PopoverPanelDefault>
        </Popover>
      )}
    </div>
  );
};

export default InlineAutoSizeStringControl;
