import { SuccessNotification } from '@models/notification';
import { AlertOptions } from '@layouts/partials/NotificationsSideBar/Alert/Alert.types';
import Alert from '@layouts/partials/NotificationsSideBar/Alert/Alert';
import s from './Alert.module.scss';

const SuccessAlert: React.FC<SuccessNotification & AlertOptions> = ({ model: { message }, onClose }) => {
  return (
    <Alert icon="check-hollow" className={s.alert_success} onClose={onClose}>
      {message}
    </Alert>
  );
};

export default SuccessAlert;
