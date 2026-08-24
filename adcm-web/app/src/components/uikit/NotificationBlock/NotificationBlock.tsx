import type { PropsWithChildren } from 'react';
import type React from 'react';
import cn from 'classnames';
import Icon from '@uikit/Icon/Icon';
import s from './NotificationBlock.module.scss';

export interface NotificationBlockProps extends PropsWithChildren {
  className?: string;
}

const NotificationBlock: React.FC<NotificationBlockProps> = ({ className, children }) => (
  <div className={cn(s.notificationBlock, className)} role="note">
    <div className={s.notificationBlock__iconWrap}>
      <Icon name="doc" size={16} className={s.notificationBlock__icon} />
    </div>
    <p className={s.notificationBlock__text}>
      <span className={s.notificationBlock__label}>Note</span>
      <span className={s.notificationBlock__content}>{children}</span>
    </p>
  </div>
);

export default NotificationBlock;
