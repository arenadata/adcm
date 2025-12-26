import { caretThickness, logicalMinimumOfWindow, minimapPadding, scaleFactor } from '@uikit/MiniMap/MiniMap.constants';
import type { GetHeightProps } from '@uikit/MiniMap/MiniMap.types';

export const getMinimapProportionalOffset = (content: HTMLDivElement, wrapper: HTMLDivElement) => {
  const contentTopOffset = content.getBoundingClientRect().y - wrapper.getBoundingClientRect().y + wrapper.scrollTop;

  return wrapper.scrollTop - contentTopOffset < 0 ? 0 : (wrapper.scrollTop - contentTopOffset) * scaleFactor;
};

export const strStyleToNumber = (strNum: string) => Number(strNum.replace('px', ''));

export const getContentVisibleRect = (contentWrapper: HTMLDivElement) => {
  if (!contentWrapper) return 0;
  const contentRect = contentWrapper.getBoundingClientRect();

  const top = Math.max(contentRect.top, 0);
  const bottom = Math.min(contentRect.bottom, window.innerHeight);

  return bottom - top;
};

export const getMinimapWrapperHeight = ({
  contentWrapper,
  scrollWrapper,
  minimapContentHeight,
  minimapTopOffset,
  buttonOffset,
}: GetHeightProps) => {
  const contentVisibleRect = getContentVisibleRect(contentWrapper);

  const wrapperStyles = getComputedStyle(scrollWrapper);
  const contentClientRect = contentWrapper.getBoundingClientRect();
  const scrollWrapperClientRect = scrollWrapper.getBoundingClientRect();
  const blockedHeight = minimapTopOffset + strStyleToNumber(wrapperStyles.paddingTop);
  const minimapCalculatedHeight = minimapContentHeight + buttonOffset + minimapPadding * 2 + caretThickness * 2;
  const pixelsTillMaxVisibleHeight =
    contentClientRect.top - scrollWrapperClientRect.top > 0 ? contentClientRect.top - scrollWrapperClientRect.top : 0;

  // If we didn't reach blocked height (it gets from prop "topOffset" it sends for example because of sticky top menu
  // or what ever), return current content wrapper height.
  // Else we calculate difference between current content wrapper height and count of pixels
  // which crossed paths with blocked height, and also we need to retreat from button above the minimap
  const minimapAvailableHeight =
    pixelsTillMaxVisibleHeight >= blockedHeight
      ? contentVisibleRect
      : contentVisibleRect - buttonOffset - (blockedHeight - pixelsTillMaxVisibleHeight);

  if (minimapAvailableHeight > minimapCalculatedHeight || minimapAvailableHeight < logicalMinimumOfWindow) {
    return minimapCalculatedHeight - buttonOffset;
  }

  if (contentVisibleRect > minimapAvailableHeight) {
    return minimapAvailableHeight;
  }

  return minimapAvailableHeight - buttonOffset;
};

export const getButtonOffset = (button: HTMLButtonElement) => {
  const btnStyles = getComputedStyle(button);

  return button.clientHeight + strStyleToNumber(btnStyles.marginBottom);
};
