import React, { useRef, useState } from 'react';
import Popover from '@uikit/Popover/Popover';
import PopoverPanelDefault from '@uikit/Popover/PopoverPanelDefault/PopoverPanelDefault';
import SingleSelectPanel from '@uikit/Select/SingleSelect/SingleSelectPanel/SingleSelectPanel';
import IconButton, { IconButtonProps } from '@uikit/IconButton/IconButton';
import { SingleSelectOptions } from '@uikit/Select/Select.types';
import { PopoverOptions } from '@uikit/Popover/Popover.types';
import { useForwardRef } from '@uikit/hooks/useForwardRef';
import cn from 'classnames';

type SelectActionProps<T> = Omit<SingleSelectOptions<T>, 'noneLabel'> &
  Omit<PopoverOptions, 'dependencyWidth'> &
  Omit<IconButtonProps, 'onClick' | 'onChange' | 'value'>;

function SelectActionComponent<T>(
  {
    options,
    value,
    onChange,
    maxHeight,
    isSearchable,
    searchPlaceholder,
    placement,
    offset,
    className,
    ...props
  }: SelectActionProps<T>,
  ref: React.ForwardedRef<HTMLButtonElement>,
) {
  const [isOpen, setIsOpen] = useState(false);
  const localRef = useRef(null);
  const reference = useForwardRef(ref, localRef);

  const handleChange = (val: T | null) => {
    setIsOpen(false);
    onChange?.(val);
  };

  return (
    <div>
      <IconButton
        //
        {...props}
        className={cn(className, { 'is-active': isOpen })}
        onClick={() => setIsOpen((prev) => !prev)}
        ref={reference}
      />

      <Popover isOpen={isOpen} onOpenChange={setIsOpen} triggerRef={localRef} placement={placement} offset={offset}>
        <PopoverPanelDefault>
          <SingleSelectPanel
            options={options}
            value={value}
            onChange={handleChange}
            maxHeight={maxHeight}
            isSearchable={isSearchable}
            searchPlaceholder={searchPlaceholder}
          />
        </PopoverPanelDefault>
      </Popover>
    </div>
  );
}

const SelectAction = React.forwardRef(SelectActionComponent) as <T>(
  _props: SelectActionProps<T>,
  _ref: React.ForwardedRef<HTMLButtonElement>,
) => ReturnType<typeof SelectActionComponent>;

export default SelectAction;
