import React from 'react';
import cn from 'classnames';
import s from './Tabs.module.scss';

export interface TabsBlockProps extends React.HTMLAttributes<HTMLDivElement> {
  variant: 'primary' | 'secondary';
}

const TabsBlock: React.FC<TabsBlockProps> = ({ children, className, variant = 'primary', ...props }) => {
  const classes = cn(className, s.tabsBlock, s[`tabsBlock_${variant}`]);

  return (
    <div className={classes} {...props}>
      {children}
    </div>
  );
};
export default TabsBlock;
