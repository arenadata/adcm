import type { AdcmLicense } from '@models/adcm';
import type React from 'react';

export interface LicensesRequiringAcceptanceList {
  id: number;
  name: string;
  displayName: string;
  license: AdcmLicense;
}

export interface LicenseAcceptanceDialogProps {
  dialogTitle: string;
  licensesRequiringAcceptanceList: LicensesRequiringAcceptanceList[];
  isOpen: boolean;
  onCloseClick: () => void;
  onBackClick?: () => void;
  onAddClick?: () => void;
  onAcceptLicense: (prototypeId: number) => void;
  customControls: React.ReactNode;
}
