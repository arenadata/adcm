import React, { useEffect } from 'react';
import MainLogo from '../partials/MainLogo/MainLogo';
import MainHeader from '../partials/MainHeader/MainHeader';
import Copyright from '../partials/Copyright/Copyright';
import s from './NonAuthLayout.module.scss';
import NotificationsSideBar from '@layouts/partials/NotificationsSideBar/NotificationsSideBar';
import { useDispatch } from '@hooks';
import { cleanupNotifications } from '@store/notificationsSlice';

const NonAuthLayout: React.FC<React.PropsWithChildren> = ({ children }) => {
  const dispatch = useDispatch();

  useEffect(() => {
    return () => {
      dispatch(cleanupNotifications());
    };
  }, [dispatch]);

  return (
    <div className={s.nonAuthLayout}>
      <div>
        <MainHeader />
        <MainLogo />
      </div>
      {children}
      <Copyright />
      <NotificationsSideBar />
    </div>
  );
};

export default NonAuthLayout;
