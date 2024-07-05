import { useMemo } from 'react';
import { GetScrollDataResponse, ScrollDataProps, ScrollOrientation } from '@uikit/ScrollBar/ScrollBarTypes';

export const defaultScrollData: GetScrollDataResponse = {
  scrollFactor: 1,
  scrollTo: 'Top',
  axisName: 'y',
  upperCasedAxis: 'Y',
};

export const getScrollData = ({ contentRef, trackRef, thumbRef, orientation }: ScrollDataProps) => {
  if (!contentRef?.current || !trackRef?.current || !thumbRef?.current) {
    return defaultScrollData;
  }

  const { magnitudeName, axisName, scrollTo } = getScrollHandlersParams(orientation);

  const lowerCasedMagnitudeName = magnitudeName.toLowerCase() as 'height' | 'width';
  const contentMagnitude = contentRef?.current?.[`client${magnitudeName}`];
  const contentScrollMagnitude = contentRef?.current?.[`scroll${magnitudeName}`];
  const scrollTrackMagnitude = trackRef?.current?.[`client${magnitudeName}`];

  const scrollFactor = contentScrollMagnitude / scrollTrackMagnitude;

  const upperCasedAxis = axisName.toUpperCase() as 'Y' | 'X';

  if (contentMagnitude !== contentScrollMagnitude) {
    thumbRef.current.style[lowerCasedMagnitudeName] = `${(contentMagnitude * 100) / contentScrollMagnitude}%`;
    trackRef.current.style.visibility = '';
  } else {
    trackRef.current.style.visibility = 'hidden';
  }

  return {
    scrollFactor,
    upperCasedAxis,
    scrollTo,
    axisName,
  };
};

interface GetScrollHandlerParams {
  magnitudeName: 'Height' | 'Width';
  axisName: 'y' | 'x';
  scrollTo: 'Left' | 'Top';
}

const getScrollHandlersParams = (orientation: ScrollOrientation): GetScrollHandlerParams => {
  return orientation === 'vertical'
    ? {
        magnitudeName: 'Height',
        axisName: 'y',
        scrollTo: 'Top',
      }
    : {
        magnitudeName: 'Width',
        axisName: 'x',
        scrollTo: 'Left',
      };
};

export const useObserver = (callBack: (entry: ResizeObserverEntry) => void) => {
  return useMemo(() => {
    return new ResizeObserver((entries) => {
      for (const entry of entries) {
        callBack(entry);
      }
    });
  }, [callBack]);
};
