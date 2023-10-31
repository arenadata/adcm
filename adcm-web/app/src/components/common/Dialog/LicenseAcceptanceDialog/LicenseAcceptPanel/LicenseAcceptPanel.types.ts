import { AdcmLicenseStatus } from '@models/adcm';

export interface LicensePanel {
  key: string;
  id: number;
  title: string;
  licenseStatus: AdcmLicenseStatus;
  licenseText?: string;
}

export interface LicenseAcceptanceDialogProps {
  license: LicensePanel;
  onAcceptLicense: (prototypeId: number) => void;
}
