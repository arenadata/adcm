import React, { useRef } from 'react';
import Input, { InputProps } from '@uikit/Input/Input';
import { useForwardRef } from '@uikit/hooks/useForwardRef';
import { createChangeEvent } from '@uikit/utils/handlerUtils';
import IconButton from '@uikit/IconButton/IconButton';

const SearchInput = React.forwardRef<HTMLInputElement, InputProps>((props, ref) => {
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
