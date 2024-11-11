import React from 'react';
import type { IconsNames } from '@uikit';
import IconButton from '@uikit/IconButton/IconButton';

export interface SynchronizedAttributeProps {
  isAllowChange: boolean;
  isSynchronized: boolean;
  onToggle: (isSynchronized: boolean) => void;
}

const synchronizedTitle = (
  <>
    <strong>Turn off synchronization</strong> with Primary configuration
  </>
);

const notSynchronizedTitle = (
  <>
    <strong>Turn on synchronization</strong> with Primary configuration
  </>
);

const synchronizedDisabledTitle = (
  <>
    This parameter needs to be <strong>synchronized</strong> with Primary configuration
  </>
);

const getTitle = (isSynchronized: boolean, isAllowChange: boolean) => {
  if (isSynchronized) {
    if (isAllowChange) {
      return synchronizedTitle;
    }
    return synchronizedDisabledTitle;
  } else {
    if (isAllowChange) {
      return notSynchronizedTitle;
    }
  }

  return null;
};

const tooltipProps = {
  placement: 'right' as const,
};

const SynchronizedAttribute = ({ isAllowChange, isSynchronized, onToggle }: SynchronizedAttributeProps) => {
  const handleClick = () => {
    if (isAllowChange) {
      onToggle(!isSynchronized);
    }
  };

  // icon should show future state (after click), not current
  const iconName: IconsNames = isSynchronized ? 'g3-unlink' : 'g3-link';
  const tooltip = getTitle(isSynchronized, isAllowChange);
  const dataTest = isSynchronized ? 'sync-linked' : 'sync-unlinked';
  const dataTestProps = `clickable=${isAllowChange ? 'true' : 'false'}`;

  return (
    <IconButton
      icon={iconName}
      onClick={handleClick}
      disabled={!isAllowChange}
      size={14}
      title={tooltip}
      tooltipProps={tooltipProps}
      data-test={dataTest}
      data-test-props={dataTestProps}
    />
  );
};

export default SynchronizedAttribute;
