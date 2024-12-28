import { useEffect, useState, useRef } from 'react';
import type { AdcmJob } from '@models/adcm';
import { AdcmJobStatus } from '@models/adcm';

export const useAutoScrollSubjobs = (tableRef: React.RefObject<HTMLTableElement>, job?: AdcmJob) => {
  const isAutoScrollInProgressRef = useRef(false);
  const [isAutoScroll, setIsAutoScroll] = useState(true);

  useEffect(() => {
    setIsAutoScroll(job?.status === AdcmJobStatus.Running);
  }, [job?.status]);

  useEffect(() => {
    if (isAutoScroll && job?.status === AdcmJobStatus.Running && tableRef.current) {
      const activeSubJobIndex = job.childJobs.findIndex((subJob) => subJob.status === AdcmJobStatus.Running);
      const tbody = tableRef.current.getElementsByTagName('tbody')[0];
      const rows = tbody.getElementsByTagName('tr');
      const row = rows[activeSubJobIndex];
      if (row) {
        const rect = row.getBoundingClientRect();
        const h = window.scrollY + rect.top + row.clientHeight - window.innerHeight;
        isAutoScrollInProgressRef.current = true;
        window.scrollTo({ top: h, behavior: 'smooth' });
      }
    }
  }, [isAutoScroll, job, tableRef]);

  useEffect(() => {
    const handleScroll = () => {
      if (!isAutoScrollInProgressRef.current && isAutoScroll) {
        setIsAutoScroll(false);
      }
    };

    const handleScrollEnd = () => {
      if (isAutoScrollInProgressRef.current && isAutoScroll) {
        isAutoScrollInProgressRef.current = false;
      }
    };

    if (job?.status === AdcmJobStatus.Running && isAutoScroll) {
      window.addEventListener('scroll', handleScroll);
      window.addEventListener('scrollend', handleScrollEnd);
    }

    return () => {
      window.removeEventListener('scroll', handleScroll);
      window.removeEventListener('scrollend', handleScrollEnd);
    };
  });

  return {
    isAutoScroll,
    setIsAutoScroll,
  };
};
