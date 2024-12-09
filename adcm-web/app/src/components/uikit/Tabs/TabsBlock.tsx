import type React from 'react';
import cn from 'classnames';
import s from './Tabs.module.scss';

export interface TabsBlockProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'primary' | 'secondary';
  justify?: 'start' | 'end';
  dataTest?: string;
}

const TabsBlock: React.FC<TabsBlockProps> = ({
  children,
  className,
  variant = 'primary',
  justify = 'start',
  dataTest = 'tab-container',
  ...props
}) => {
  const classes = cn(className, s.tabsBlock, s[`tabsBlock_${variant}`], s[`tabsBlock_${justify}Justify`]);

  return (
    <div className={classes} {...props} data-test={dataTest}>
      {children}
    </div>
  );
};
export default TabsBlock;
