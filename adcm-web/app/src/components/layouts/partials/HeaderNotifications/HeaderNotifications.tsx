import React, { useRef, useState } from 'react';
import { ReactComponent as Bell } from './images/complex-bell.svg';
import s from './HeaderNotifications.module.scss';
import iconButtonStyles from '@uikit/IconButton/IconButton.module.scss';
import cn from 'classnames';
import { Popover } from '@uikit';
import { useDebounce, useDispatch, useRequestTimer, useStore } from '@hooks';
import JobInfo from '@layouts/partials/HeaderNotifications/JobInfo/JobInfo';
import { AdcmJobStatus } from '@models/adcm';
import { getJobs, refreshJobs } from '@store/adcm/bell/bellSlice';
import Spinner from '@uikit/Spinner/Spinner';
import { defaultDebounceDelay } from '@constants';

const HeaderNotifications: React.FC = () => {
  const dispatch = useDispatch();
  const [isOpen, setIsOpen] = useState(false);
  const localRef = useRef(null);

  const jobs = useStore((s) => s.adcm.bell.jobs);
  const isLoading = useStore((s) => s.adcm.bell.isLoading);
  const requestFrequency = useStore((s) => s.adcm.bell.requestFrequency);
  const { filter, sortParams, paginationParams } = useStore((s) => s.adcm.bell);

  const status = jobs?.[0]?.status;

  const bellButtonClassName = cn(
    s.headerNotifications,
    iconButtonStyles.iconButton,
    iconButtonStyles.iconButton_primary,
    {
      [s.headerNotifications_done]: status === undefined,
      [s.headerNotifications_failed]: status === AdcmJobStatus.Failed,
      [s.headerNotifications_success]: status === AdcmJobStatus.Success,
      [s.headerNotifications_running]: status === AdcmJobStatus.Running,
      [s.headerNotifications_locked]: status === AdcmJobStatus.Locked,
    },
  );

  const handleBellClick = () => {
    dispatch(getJobs());
    setIsOpen((prev) => !prev);
  };

  const debounceGetData = useDebounce(() => {
    dispatch(getJobs());
  }, defaultDebounceDelay);

  const debounceRefreshData = useDebounce(() => {
    dispatch(refreshJobs());
  }, defaultDebounceDelay);

  useRequestTimer(debounceGetData, debounceRefreshData, requestFrequency, [filter, sortParams, paginationParams]);

  return (
    <>
      <button ref={localRef} className={bellButtonClassName} onClick={handleBellClick}>
        <Bell width={28} />
      </button>
      <Popover isOpen={isOpen} onOpenChange={setIsOpen} triggerRef={localRef}>
        <div className={s.bellPopoverPanel}>
          {isLoading && (
            <div className={s.bellPopoverPanel__spinner}>
              <Spinner />
            </div>
          )}
          {!isLoading && <JobInfo jobs={jobs} />}
        </div>
      </Popover>
    </>
  );
};

export default HeaderNotifications;
