import React from 'react';
import { PopoverPanelProps } from '@uikit/Popover/Popover.types';

const PopoverPanelDefault = React.forwardRef<HTMLDivElement, PopoverPanelProps>(
  ({ children, className, ...style }, ref) => {
    return (
      <div ref={ref} style={style} className={className}>
        {children}
      </div>
    );
  },
);

PopoverPanelDefault.displayName = 'PopoverPanelDefault';
export default PopoverPanelDefault;
