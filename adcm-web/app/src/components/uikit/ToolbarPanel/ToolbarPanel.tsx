import type { HTMLAttributes } from 'react';
import type React from 'react';
import cn from 'classnames';
import s from './ToolbarPanel.module.scss';

interface ToolbarPanelProps extends HTMLAttributes<HTMLDivElement> {
  justify?: 'start' | 'end' | 'justify';
}

const ToolbarPanel: React.FC<ToolbarPanelProps> = ({ className, children, justify = 'justify', ...props }) => {
  const classes = cn(className, s.toolbarPanel, s[`toolbarPanel_${justify}`]);

  return (
    <div className={classes} {...props}>
      {children}
    </div>
  );
};

export default ToolbarPanel;
