import { RefObject } from 'react';

export type ScrollPosition = 'top' | 'left' | 'bottom' | 'right';

export type ScrollOrientation = 'vertical' | 'horizontal';

export interface Scroll {
  orientation: ScrollOrientation;
}

export interface ScrollBarProps extends Scroll {
  contentRef: RefObject<HTMLDivElement>;
  trackClasses?: string;
  thumbClasses?: string;
  thumbCaptureRadius?: number;
}

export interface GetScrollDataResponse {
  scrollFactor: number;
  scrollTo: 'Top' | 'Left';
  axisName: 'y' | 'x';
  upperCasedAxis: 'Y' | 'X';
}

export interface ScrollDataProps {
  contentRef: RefObject<HTMLDivElement>;
  trackRef: RefObject<HTMLDivElement>;
  thumbRef: RefObject<HTMLDivElement>;
  orientation: ScrollOrientation;
}
