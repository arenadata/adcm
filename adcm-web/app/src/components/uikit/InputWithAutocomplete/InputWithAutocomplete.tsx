import { useState, useRef, useMemo } from 'react';
import Input, { InputProps } from '@uikit/Input/Input';
import Popover from '@uikit/Popover/Popover';
import { createChangeEvent } from '@utils/handlerUtils';
import PopoverPanelDefault from '@uikit/Popover/PopoverPanelDefault/PopoverPanelDefault';
import s from './InputWithAutocomplete.module.scss';
import cn from 'classnames';

export interface InputWithAutoCompleteProps extends InputProps {
  suggestions: string[];
}

const InputWithAutoComplete = ({ suggestions, value, onChange, onFocus, ...restProps }: InputWithAutoCompleteProps) => {
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

  const handleSelectSuggestion = (e: React.MouseEvent<HTMLLIElement>) => {
    const newValue = e.currentTarget.dataset.suggestion;
    if (newValue) {
      const changeEvent = createChangeEvent(inputRef.current);
      changeEvent.target.value = newValue;
      onChange?.(changeEvent);
    }
  };

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
          <ul className={cn(s.suggestionsList, 'scroll')}>
            {filteredSuggestions.map((suggestion) => (
              <li
                key={suggestion}
                className={s.suggestion}
                data-suggestion={suggestion}
                onClick={handleSelectSuggestion}
              >
                {suggestion}
              </li>
            ))}
          </ul>
        </PopoverPanelDefault>
      </Popover>
    </>
  );
};

export default InputWithAutoComplete;
