import React, { HTMLAttributes } from 'react';
import cn from 'classnames';
import s from './Panel.module.scss';

interface PanelProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'primary' | 'secondary';
}

const Panel: React.FC<PanelProps> = ({ className, children, variant = 'primary', ...props }) => {
  return (
    <div className={cn(s.panel, s[`panel_${variant}`], className)} {...props}>
      {children}
    </div>
  );
};

export default Panel;
