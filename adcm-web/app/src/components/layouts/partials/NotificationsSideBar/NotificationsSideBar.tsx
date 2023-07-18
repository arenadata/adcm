import React, { useEffect } from 'react';
import s from './NotificationsSideBar.module.scss';
import { useDispatch, useStore } from '@hooks';
import { Notification, NotificationVariant } from '@models/notification';
import ErrorAlert from '@layouts/partials/NotificationsSideBar/Alert/ErrorAlert';
import InfoAlert from '@layouts/partials/NotificationsSideBar/Alert/InfoAlert';
import { closeNotification } from '@store/notificationsSlice';

const NotificationItem: React.FC<Notification> = (props) => {
  const { ttl, variant, id } = props;
  const dispatch = useDispatch();
  const removeNotification = (id: string) => {
    dispatch(closeNotification(id));
  };

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    if (ttl) {
      timer = setTimeout(() => {
        removeNotification(id);
      }, ttl);
    }

    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (variant === NotificationVariant.Error) {
    return <ErrorAlert {...props} onClose={() => removeNotification(id)} />;
  }
  if (variant === NotificationVariant.Info) {
    return <InfoAlert {...props} onClose={() => removeNotification(id)} />;
  }

  return null;
};

const NotificationsSideBar: React.FC = () => {
  const { notifications } = useStore((s) => s.notifications);

  return (
    <div className={s.notificationsSideBar}>
      {notifications.map((item) => {
        return <NotificationItem key={item.id} {...item} />;
      })}
    </div>
  );
};
export default NotificationsSideBar;
