import type { CSSProperties } from 'react';
import type React from 'react';
import cn from 'classnames';
import s from './WarningMessage.module.scss';
import Icon from '@uikit/Icon/Icon';

export interface WarningProps extends React.PropsWithChildren {
  className?: string;
  variant?: 'warning' | 'info';
  action?: React.ReactNode;
  innerMaxHeight?: CSSProperties['maxHeight'];
}

const iconByVariant = {
  warning: 'alert-circle',
  info: 'info',
} as const;

const WarningMessage = ({ className, children, variant = 'warning', action, innerMaxHeight = '104' }: WarningProps) => (
  <div className={cn(s.warning, s[`warning_${variant}`], className)}>
    <Icon name={iconByVariant[variant]} size={28} className={s.warning__icon} />
    <div className={cn(s.warning__text, 'scroll')} style={{ maxHeight: innerMaxHeight }}>
      {children}
    </div>
    {action && <div className={s.warning__action}>{action}</div>}
  </div>
);

export default WarningMessage;
