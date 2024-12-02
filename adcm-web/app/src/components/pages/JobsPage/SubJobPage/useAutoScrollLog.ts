import type { AdcmSubJob } from '@models/adcm';
import { AdcmJobStatus } from '@models/adcm';
import { useEffect, useState } from 'react';

export const useAutoScrollLog = (subJob?: AdcmSubJob) => {
  const [isAutoScroll, setIsAutoScroll] = useState(true);

  useEffect(() => {
    const onUserScrollHandler = () => {
      setIsAutoScroll(false);
    };

    if (subJob?.status === AdcmJobStatus.Running && isAutoScroll) {
      window.addEventListener('scroll', onUserScrollHandler);
    }

    return () => {
      window.removeEventListener('scroll', onUserScrollHandler);
    };
  }, [subJob?.status, isAutoScroll]);

  return {
    isAutoScroll,
    setIsAutoScroll,
  };
};
