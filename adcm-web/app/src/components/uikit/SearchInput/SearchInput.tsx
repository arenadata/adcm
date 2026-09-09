import React, { useRef } from 'react';
import cn from 'classnames';
import type { InputProps } from '@uikit/Input/Input';
import Input from '@uikit/Input/Input';
import { useForwardRef } from '@hooks';
import IconButton from '@uikit/IconButton/IconButton';
import { useDebouncedSearchValue } from './useDebouncedSearchValue';

export type SearchInputProps = Omit<InputProps, 'startAdornment' | 'endAdornment'> & {
  debounceDelay?: number;
};

const SearchInput = React.forwardRef<HTMLInputElement, SearchInputProps>(
  ({ className, debounceDelay = 0, value, onChange, ...props }, ref) => {
    const localRef = useRef<HTMLInputElement>(null);
    const reference = useForwardRef(ref, localRef);
    const search = useDebouncedSearchValue(value, onChange, localRef, debounceDelay);

    return (
      <Input
        {...props}
        className={cn(className, 'search-input')}
        ref={reference}
        value={search.localValue}
        onChange={search.onChange}
        startAdornment={<IconButton icon="g2-magnifying-glass" size={20} />}
        endAdornment={search.localValue ? <IconButton icon="g2-close" onClick={search.clear} size={20} /> : null}
        size={14}
      />
    );
  },
);

SearchInput.displayName = 'SearchInput';
export default SearchInput;
