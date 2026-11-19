import { useState, useRef, useMemo, useCallback } from 'react';
import type { InputProps } from '@uikit/Input/Input';
import Input from '@uikit/Input/Input';
import Popover from '@uikit/Popover/Popover';
import { createChangeEvent } from '@utils/handlerUtils';
import PopoverPanelDefault from '@uikit/Popover/PopoverPanelDefault/PopoverPanelDefault';
import { SuggestionsList } from './SuggestionsList/SuggestionsList';

export interface InputWithAutoCompleteProps extends InputProps {
  suggestions: string[];
  isVirtualized?: boolean;
}

const InputWithAutoComplete = ({
  suggestions,
  isVirtualized = false,
  value,
  onChange,
  onFocus,
  ...restProps
}: InputWithAutoCompleteProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const filteredSuggestions = useMemo(
    () => (value ? suggestions.filter((s) => s.startsWith(value as string)) : suggestions),
    [suggestions, value],
  );

  const handleFocus = (e: React.FocusEvent<HTMLInputElement>) => {
    setIsOpen(true);
    onFocus?.(e);
  };

  const handleSelectSuggestion = useCallback(
    (suggestion: string) => {
      const changeEvent = createChangeEvent(inputRef.current);
      changeEvent.target.value = suggestion;
      onChange?.(changeEvent);
    },
    [onChange],
  );

  return (
    <>
      <Input ref={inputRef} value={value} onFocus={handleFocus} onChange={onChange} {...restProps} />
      <Popover
        isOpen={isOpen && filteredSuggestions.length > 0}
        onOpenChange={setIsOpen}
        triggerRef={inputRef}
        dependencyWidth="parent"
        placement="bottom-start"
        offset={8}
      >
        <PopoverPanelDefault>
          <SuggestionsList
            suggestions={filteredSuggestions}
            onSelect={handleSelectSuggestion}
            isVirtualized={isVirtualized}
          />
        </PopoverPanelDefault>
      </Popover>
    </>
  );
};

export default InputWithAutoComplete;
