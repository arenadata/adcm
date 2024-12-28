import type React from 'react';
import cn from 'classnames';
import s from './WarningMessage.module.scss';
import Icon from '@uikit/Icon/Icon';

export interface WarningProps extends React.PropsWithChildren {
  className?: string;
}

const WarningMessage = ({ className, children }: WarningProps) => (
  <div className={cn(s.warning, className)}>
    <Icon name="alert-circle" size={28} className={s.warning__icon} />
    <div className={cn(s.warning__text, 'scroll')}>{children}</div>
  </div>
);

export default WarningMessage;
