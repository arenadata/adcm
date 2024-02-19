import React, { useMemo, useRef, useState } from 'react';
import { InputProps } from '@uikit/Input/Input';
import SingleSelectPanel from '@uikit/Select/SingleSelect/SingleSelectPanel/SingleSelectPanel';
import Popover from '@uikit/Popover/Popover';
import { SingleSelectOptions } from '@uikit/Select/Select.types';
import { useForwardRef } from '@hooks';
import CommonSelectField from '@uikit/Select/CommonSelect/CommonSelectField/CommonSelectField';
import PopoverPanelDefault from '@uikit/Popover/PopoverPanelDefault/PopoverPanelDefault';
import { PopoverOptions } from '@uikit/Popover/Popover.types';

export type SelectProps<T> = SingleSelectOptions<T> &
  PopoverOptions &
  Omit<InputProps, 'endAdornment' | 'startAdornment' | 'readOnly' | 'onChange' | 'value'> & { dataTest?: string };

function SelectComponent<T>(
  {
    options,
    value,
    onChange,
    noneLabel,
    maxHeight = 200,
    isSearchable,
    searchPlaceholder,
    containerRef,
    placement,
    offset,
    dependencyWidth = 'min-parent',
    dataTest = 'select-popover',
    ...props
  }: SelectProps<T>,
  ref: React.ForwardedRef<HTMLInputElement>,
) {
  const [isOpen, setIsOpen] = useState(false);
  const localContainerRef = useRef(null);
  const containerReference = useForwardRef(localContainerRef, containerRef);

  const handleChange = (val: T | null) => {
    setIsOpen(false);
    onChange?.(val);
  };

  const selectedOptionLabel = useMemo(() => {
    const currentOption = options.find(({ value: val }) => val === value);
    return currentOption?.label ?? '';
  }, [options, value]);

  return (
    <div>
      <CommonSelectField
        {...props}
        ref={ref}
        onClick={() => setIsOpen((prev) => !prev)}
        isOpen={isOpen}
        value={selectedOptionLabel}
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
        <PopoverPanelDefault data-test={dataTest}>
          <SingleSelectPanel
            options={options}
            value={value}
            onChange={handleChange}
            noneLabel={noneLabel}
            maxHeight={maxHeight}
            isSearchable={isSearchable}
            searchPlaceholder={searchPlaceholder}
          />
        </PopoverPanelDefault>
      </Popover>
    </div>
  );
}

const Select = React.forwardRef(SelectComponent) as <T>(
  _props: SelectProps<T>,
  _ref: React.ForwardedRef<HTMLInputElement>,
) => ReturnType<typeof SelectComponent>;

export default Select;
