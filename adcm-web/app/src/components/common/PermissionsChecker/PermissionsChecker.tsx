import s from './PermissionsChecker.module.scss';
import { RequestState } from '@models/loadState';
import NotFoundPage from '@pages/NotFoundPage/NotFoundPage';
import AccessDeniedPage from '@pages/AccessDeniedPage/AccessDeniedPage';
import { Spinner } from '@uikit';

interface WithHttpResponseRouteProps {
  children?: React.ReactNode;
  requestState?: RequestState;
}

const PermissionsChecker = ({ children, requestState }: WithHttpResponseRouteProps) => {
  if (requestState === RequestState.Pending) {
    return (
      <div className={s.spinnerWrapper}>
        <Spinner />
      </div>
    );
  }

  if (requestState === RequestState.AccessDenied) {
    return <AccessDeniedPage />;
  }

  if (requestState === RequestState.NotFound) {
    return <NotFoundPage />;
  }

  if (requestState === RequestState.Completed) {
    return <>{children}</>;
  }
};

export default PermissionsChecker;
