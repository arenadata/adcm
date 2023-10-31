import React, { useState } from 'react';
import s from './BundleOverviewAcceptPanel.module.scss';
import { Button, Checkbox } from '@uikit';
import { useDispatch } from '@hooks';
import { acceptBundleLicenseWithUpdate } from '@store/adcm/bundle/bundleSlice';

interface BundleOverviewAcceptPanelProps {
  bundleId?: number;
  prototypeId?: number;
  isLicenseAccepted: boolean;
}

const BundleOverviewAcceptPanel = ({ prototypeId, bundleId, isLicenseAccepted }: BundleOverviewAcceptPanelProps) => {
  const dispatch = useDispatch();
  const [isDisabled, setIsDisabled] = useState<boolean>(true);

  const checkboxHandler = () => {
    setIsDisabled((prev) => !prev);
  };

  const acceptLicenseHandler = () => {
    if (prototypeId && bundleId) {
      dispatch(acceptBundleLicenseWithUpdate({ bundleId, prototypeId }));
      setIsDisabled(false);
    }
  };

  return (
    <div className={s.acceptPanel}>
      <Checkbox onClick={checkboxHandler} label="I've read text of License Agreement" disabled={isLicenseAccepted} />
      <Button onClick={acceptLicenseHandler} disabled={isDisabled || isLicenseAccepted}>
        Accept
      </Button>
    </div>
  );
};

export default BundleOverviewAcceptPanel;
