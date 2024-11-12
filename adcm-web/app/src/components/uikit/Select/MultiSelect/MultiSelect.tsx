import React, { useRef, useState } from 'react';
import type { InputProps } from '@uikit/Input/Input';
import MultiSelectPanel from './MultiSelectPanel/MultiSelectPanel';
import Popover from '@uikit/Popover/Popover';
import type { MultiSelectOptions } from '@uikit/Select/Select.types';
import { useForwardRef } from '@hooks';
import CommonSelectField from '@uikit/Select/CommonSelect/CommonSelectField/CommonSelectField';
import PopoverPanelDefault from '@uikit/Popover/PopoverPanelDefault/PopoverPanelDefault';
import type { PopoverOptions } from '@uikit/Popover/Popover.types';
import MultiSelectResults from '@uikit/Select/MultiSelect/MultiSelectResults/MultiSelectResults';

export type MultiSelectProps<T> = MultiSelectOptions<T> &
  PopoverOptions &
  Omit<InputProps, 'endAdornment' | 'startAdornment' | 'readOnly' | 'onChange' | 'value'>;

function MultiSelectComponent<T>(
  {
    options,
    value,
    onChange,
    checkAllLabel,
    maxHeight,
    isSearchable,
    searchPlaceholder,
    containerRef,
    placement,
    offset,
    dependencyWidth = 'min-parent',
    ...props
  }: MultiSelectProps<T>,
  ref: React.ForwardedRef<HTMLInputElement>,
) {
  const [isOpen, setIsOpen] = useState(false);
  const localContainerRef = useRef(null);
  const containerReference = useForwardRef(localContainerRef, containerRef);

  const handleChange = (values: T[]) => {
    onChange?.(values);
  };

  return (
    <>
      <CommonSelectField
        {...props}
        ref={ref}
        onClick={() => setIsOpen((prev) => !prev)}
        isOpen={isOpen}
        containerRef={containerReference}
      />
      <Popover
        isOpen={isOpen}
        onOpenChange={setIsOpen}
        triggerRef={localContainerRef}
        dependencyWidth={dependencyWidth}
        placement={placement}
        offset={offset}
      >
        <PopoverPanelDefault>
          <MultiSelectPanel
            options={options}
            value={value}
            onChange={handleChange}
            checkAllLabel={checkAllLabel}
            maxHeight={maxHeight}
            isSearchable={isSearchable}
            searchPlaceholder={searchPlaceholder}
          />
        </PopoverPanelDefault>
      </Popover>
      <MultiSelectResults value={value} onChange={onChange} options={options} />
    </>
  );
}

const MultiSelect = React.forwardRef(MultiSelectComponent) as <T>(
  _props: MultiSelectProps<T>,
  _ref: React.ForwardedRef<HTMLInputElement>,
) => ReturnType<typeof MultiSelectComponent>;

export default MultiSelect;
