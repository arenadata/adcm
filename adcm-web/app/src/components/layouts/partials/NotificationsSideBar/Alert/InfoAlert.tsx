import React from 'react';
import Alert from './Alert';
import type { InfoNotification } from '@models/notification';
import type { AlertOptions } from './Alert.types';

import s from './Alert.module.scss';

const InfoAlert: React.FC<InfoNotification & AlertOptions> = ({ model: { message }, onClose }) => {
  return (
    <Alert icon="lamp" className={s.alert_info} onClose={onClose}>
      {message}
    </Alert>
  );
};

export default InfoAlert;
