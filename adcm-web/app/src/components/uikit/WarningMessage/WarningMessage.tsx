import type { CSSProperties } from 'react';
import type React from 'react';
import cn from 'classnames';
import s from './WarningMessage.module.scss';
import Icon from '@uikit/Icon/Icon';

export interface WarningProps extends React.PropsWithChildren {
  className?: string;
  innerMaxHeight?: CSSProperties['maxHeight'];
}

const WarningMessage = ({ className, children, innerMaxHeight = '104' }: WarningProps) => (
  <div className={cn(s.warning, className)}>
    <Icon name="alert-circle" size={28} className={s.warning__icon} />
    <div className={cn(s.warning__text, 'scroll')} style={{ maxHeight: innerMaxHeight }}>
      {children}
    </div>
  </div>
);

export default WarningMessage;
