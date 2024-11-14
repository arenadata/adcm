import type { AdcmTask } from '@models/adcm';
import { AdcmJobStatus } from '@models/adcm';
import { useParams } from 'react-router-dom';
import { useEffect, useRef, useState } from 'react';

export const useJobLogAutoScroll = (task: AdcmTask) => {
  const isUserScrollRef = useRef(false);
  const isAutoScrollRef = useRef(true);
  const [isAutoScrollState, setIsAutoScrollState] = useState(true);
  const props = useParams();
  const { withAutoStop } = props;

  const setIsAutoScroll = (state: boolean) => {
    if (!withAutoStop) return;
    setIsAutoScrollState(state);
    isAutoScrollRef.current = state;
  };

  const toggleIsAutoScroll = () => {
    isAutoScrollRef.current = !isAutoScrollRef.current;
    setIsAutoScrollState((prev) => !prev);
  };

  useEffect(() => {
    const onUserScrollHandler = () => {
      if (isUserScrollRef.current) {
        setIsAutoScroll(false);
      }
    };

    const onEndHandler = () => {
      isUserScrollRef.current = true;
    };

    if (task.status === AdcmJobStatus.Running && isAutoScrollState) {
      window.addEventListener('scroll', onUserScrollHandler);
      window.addEventListener('scrollend', onEndHandler);
    }

    return () => {
      window.removeEventListener('scroll', onUserScrollHandler);
      window.removeEventListener('scrollend', onEndHandler);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [task.status, isAutoScrollRef, isAutoScrollState]);

  return {
    isAutoScrollState,
    toggleIsAutoScroll,
    isUserScrollRef,
    setIsAutoScroll,
  };
};
