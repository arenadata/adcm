import type { ChangeEvent } from 'react';
import React, { useState } from 'react';
import s from './LicenseAcceptPanel.module.scss';
import { Button, Checkbox } from '@uikit';
import { AdcmLicenseStatus } from '@models/adcm';
import cn from 'classnames';
import type { LicenseAcceptanceDialogProps } from '@commonComponents/Dialog/LicenseAcceptanceDialog/LicenseAcceptPanel/LicenseAcceptPanel.types';

const LicenseAcceptPanel: React.FC<LicenseAcceptanceDialogProps> = ({
  license,
  onAcceptLicense,
}: LicenseAcceptanceDialogProps) => {
  const [isLicenseChecked, setIsLicenseChecked] = useState<boolean>(false);
  const isLicenseAccepted = license.licenseStatus === AdcmLicenseStatus.Accepted;

  const toggleLicenseCheckbox = (event: ChangeEvent<HTMLInputElement>) => {
    setIsLicenseChecked(event.target.checked);
  };

  const acceptLicenseHandler = (prototypeId: number) => () => {
    onAcceptLicense(prototypeId);
  };

  return (
    <div key={license.key}>
      <div className={cn(s.acceptPanel, isLicenseAccepted ? s.acceptPanel_licenseAccepted : '')}>
        <Checkbox
          onChange={toggleLicenseCheckbox}
          label="I've read text of License Agreement"
          checked={isLicenseChecked || isLicenseAccepted}
          className={isLicenseAccepted ? s.checkbox_licenseAccepted : ''}
        />
        <Button
          onClick={acceptLicenseHandler(license.id)}
          disabled={!isLicenseChecked || isLicenseAccepted}
          className={isLicenseAccepted ? s.button_licenseAccepted : ''}
        >
          {isLicenseAccepted ? 'Accepted' : 'Accept'}
        </Button>
      </div>
      <div className={cn(s.licenseField, 'scroll')}>
        <pre>{license.licenseText}</pre>
      </div>
    </div>
  );
};

export default LicenseAcceptPanel;
