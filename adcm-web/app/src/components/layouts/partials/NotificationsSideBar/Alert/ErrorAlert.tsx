import React from 'react';
import { ErrorNotification } from '@models/notification';
import Alert from './Alert';
import { AlertOptions } from './Alert.types';

import s from './Alert.module.scss';

const ErrorAlert: React.FC<ErrorNotification & AlertOptions> = ({ model: { message }, onClose }) => {
  return (
    <Alert icon="triangle-alert" className={s.alert_error} onClose={onClose}>
      {message}
    </Alert>
  );
};

export default ErrorAlert;
