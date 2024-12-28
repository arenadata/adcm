import React from 'react';
import type { PopoverPanelProps } from '@uikit/Popover/Popover.types';
import cn from 'classnames';
import s from './PopoverPanelDefault.module.scss';

const PopoverPanelDefault = React.forwardRef<HTMLDivElement, PopoverPanelProps>(
  ({ children, className, ...props }, ref) => {
    return (
      <div ref={ref} {...props} className={cn(className, s.popoverPanelDefault)}>
        {children}
      </div>
    );
  },
);

PopoverPanelDefault.displayName = 'PopoverPanelDefault';
export default PopoverPanelDefault;
