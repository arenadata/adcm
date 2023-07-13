import React from 'react';
import cn from 'classnames';
import { Button, Icon, IconsNames } from '@uikit';

import s from './Alert.module.scss';
import { AlertOptions } from '@layouts/partials/NotificationsSideBar/Alert/Alert.types';

interface AlertProps extends AlertOptions {
  icon: Extract<IconsNames, 'lamp' | 'triangle-alert'>;
}

const Alert: React.FC<AlertProps> = ({ children, className, icon, onClose }) => {
  return (
    <div className={cn(className, s.alert)}>
      <Icon name={icon} size={36} className={s.alert__icon} />
      <div>{children}</div>
      <Button className={s.alert__button} onClick={onClose}>
        Got it
      </Button>
    </div>
  );
};

export default Alert;
