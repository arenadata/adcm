import React, { type CSSProperties, useMemo } from 'react';
import cn from 'classnames';
import s from './FlexGroup.module.scss';

interface FlexGroupProps extends React.HTMLAttributes<HTMLDivElement> {
  gap?: CSSProperties['gap'];
  justifyContent?: CSSProperties['justifyContent'];
}

const FlexGroup = React.forwardRef<HTMLDivElement, FlexGroupProps>(
  ({ children, className, gap, justifyContent, style, ...props }, ref) => {
    const innerStyle = useMemo(() => ({ gap, justifyContent, ...style }), [gap, justifyContent, style]);

    return (
      <div className={cn(className, s.flexGroup)} style={innerStyle} {...props} ref={ref}>
        {children}
      </div>
    );
  },
);

export default FlexGroup;
