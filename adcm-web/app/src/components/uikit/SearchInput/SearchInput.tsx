import React, { useRef } from 'react';
import cn from 'classnames';
import type { InputProps } from '@uikit/Input/Input';
import Input from '@uikit/Input/Input';
import { useForwardRef } from '@hooks';
import { createChangeEvent } from '@utils/handlerUtils';
import IconButton from '@uikit/IconButton/IconButton';

const SearchInput = React.forwardRef<HTMLInputElement, InputProps>(({ className, ...props }, ref) => {
  const localRef = useRef<HTMLInputElement>(null);
  const reference = useForwardRef(ref, localRef);

  const handleIconClick = () => {
    if (props.value && localRef.current) {
      const event = createChangeEvent(localRef.current);
      event.target.value = '';
      props.onChange?.(event);
    }
  };

  return (
    <Input
      {...props}
      className={cn(className, 'search-input')}
      ref={reference}
      endAdornment={
        <IconButton icon={props.value ? 'g2-close' : 'g2-magnifying-glass'} onClick={handleIconClick} size={20} />
      }
      size={14}
    />
  );
});

SearchInput.displayName = 'SearchInput';
export default SearchInput;
