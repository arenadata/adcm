import React, { cloneElement, useRef, useState } from 'react';
import { useForwardRef } from '@hooks';
import type { SingleSelectOptions } from '@uikit/Select/Select.types';
import type { PopoverOptions } from '@uikit/Popover/Popover.types';
import type { ChildWithRef } from '@uikit/types/element.types';
import Popover from '@uikit/Popover/Popover';
import PopoverPanelDefault from '@uikit/Popover/PopoverPanelDefault/PopoverPanelDefault';
import SingleSelectPanel from '@uikit/Select/SingleSelect/SingleSelectPanel/SingleSelectPanel';
import cn from 'classnames';

type ActionMenuProps<T> = Omit<SingleSelectOptions<T>, 'noneLabel'> &
  Omit<PopoverOptions, 'dependencyWidth'> & {
    children: ChildWithRef;
  };

const ActionMenu = <T,>({
  children,
  onChange,
  placement,
  offset,
  value,
  maxHeight = 300,
  ...props
}: ActionMenuProps<T>) => {
  const [isOpen, setIsOpen] = useState(false);
  const localRef = useRef(null);
  const reference = useForwardRef(localRef, children.ref);

  const handleChange = (val: T | null) => {
    setIsOpen(false);
    onChange?.(val);
  };

  return (
    <>
      {React.Children.only(
        cloneElement(children, {
          ref: reference,
          ...children.props,
          className: cn(children.props.className, { 'is-active': isOpen }),
          onClick: (event: React.MouseEvent) => {
            setIsOpen((prev) => !prev);
            children.props.onClick?.(event);
          },
        }),
      )}
      <Popover isOpen={isOpen} onOpenChange={setIsOpen} triggerRef={localRef} placement={placement} offset={offset}>
        <PopoverPanelDefault>
          <SingleSelectPanel
            //
            {...props}
            value={value}
            onChange={handleChange}
            maxHeight={maxHeight}
          />
        </PopoverPanelDefault>
      </Popover>
    </>
  );
};
export default ActionMenu;
