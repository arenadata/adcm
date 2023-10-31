import React, { useState } from 'react';
import Panel from '@uikit/Panel/Panel';
import { Button, Checkbox } from '@uikit';
import s from './LicenseAcceptancePanel.module.scss';
import { AdcmLicenseStatus } from '@models/adcm';
import cn from 'classnames';

interface LicenseAcceptancePanelProps {
  className?: string;
  licenseStatus: AdcmLicenseStatus;
  label?: React.ReactNode;
  onAccept: () => void;
}

const LicenseAcceptancePanel: React.FC<LicenseAcceptancePanelProps> = ({
  onAccept,
  className,
  licenseStatus,
  label = 'I have read text of License Agreement',
}) => {
  const isLicenseAccepted = licenseStatus === AdcmLicenseStatus.Accepted;

  const [isChecked, setIsChecked] = useState(isLicenseAccepted);

  const handleChangeAcceptance = (event: React.ChangeEvent<HTMLInputElement>) => {
    setIsChecked(event.target.checked);
  };

  return (
    <Panel className={cn(s.licenseAcceptancePanel, className)}>
      <Checkbox checked={isChecked} onChange={handleChangeAcceptance} label={label} disabled={isLicenseAccepted} />
      <Button onClick={onAccept} disabled={!isChecked || isLicenseAccepted}>
        Accept
      </Button>
    </Panel>
  );
};
export default LicenseAcceptancePanel;
