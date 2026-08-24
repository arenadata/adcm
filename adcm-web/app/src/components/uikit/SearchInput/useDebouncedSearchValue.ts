import type React from 'react';
import { useEffect, useState } from 'react';
import { useDebouncedValue, useDidUpdate } from '@hooks';
import { createChangeEvent } from '@utils/handlerUtils';

type ChangeHandler = (event: React.ChangeEvent<HTMLInputElement>) => void;

export const useDebouncedSearchValue = (
  value: React.InputHTMLAttributes<HTMLInputElement>['value'],
  onChange: ChangeHandler | undefined,
  inputRef: React.RefObject<HTMLInputElement | null>,
  delay: number,
) => {
  const [localValue, setLocalValue] = useState(String(value ?? ''));
  const debouncedValue = useDebouncedValue(localValue, delay);

  useEffect(() => {
    setLocalValue(String(value ?? ''));
  }, [value]);

  useDidUpdate(() => {
    if (!onChange || !inputRef.current || debouncedValue === String(value ?? '')) {
      return;
    }

    inputRef.current.value = debouncedValue;
    onChange(createChangeEvent(inputRef.current));
  }, [debouncedValue]);

  const emitChange = (nextValue: string) => {
    setLocalValue(nextValue);

    if (!onChange || !inputRef.current) {
      return;
    }

    inputRef.current.value = nextValue;
    onChange(createChangeEvent(inputRef.current));
  };

  return {
    localValue,
    onChange: (event: React.ChangeEvent<HTMLInputElement>) => setLocalValue(event.target.value),
    clear: () => emitChange(''),
  };
};
