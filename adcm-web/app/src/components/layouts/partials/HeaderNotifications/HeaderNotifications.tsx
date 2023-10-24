import React, { useRef, useState } from 'react';
import { ReactComponent as Bell } from './images/complex-bell.svg';
import s from './HeaderNotifications.module.scss';
import iconButtonStyles from '@uikit/IconButton/IconButton.module.scss';
import cn from 'classnames';
import { Button, Popover } from '@uikit';
import { useDebounce, useDispatch, useRequestTimer, useStore } from '@hooks';
import JobInfoRow from '@layouts/partials/HeaderNotifications/JobInfoRow/JobInfoRow';
import { AdcmJobStatus } from '@models/adcm';
import { cleanupBell, getJobs, refreshJobs } from '@store/adcm/bell/bellSlice';
import { SpinnerPanel } from '@uikit/Spinner/Spinner';
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

  const handleAcknowledgeClick = () => {
    dispatch(cleanupBell());
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
          <div className={s.bellPopoverPanel_content}>
            {isLoading && <SpinnerPanel />}
            {!isLoading && jobs.map((job) => <JobInfoRow key={job.id} job={job} />)}
          </div>
          <div className={s.bellPopoverPanel_footer}>
            <Button className={s.acknowledgeButton} variant="clear" onClick={handleAcknowledgeClick}>
              Acknowledge
            </Button>
          </div>
        </div>
      </Popover>
    </>
  );
};

export default HeaderNotifications;
