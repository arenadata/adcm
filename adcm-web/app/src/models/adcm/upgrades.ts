import { AdcmPrototype } from '@models/adcm/prototype';
import { AdcmDynamicActionDetails, AdcmDynamicActionRunConfig } from '@models/adcm/dynamicAction';
import { AdcmLicenseStatus } from '@models/adcm/license';

export interface AdcmUpgradeShort {
  id: number;
  name: string;
  displayName: string;
}

type AdcmUnacceptedServicesPrototype = Omit<AdcmPrototype, 'type' | 'bundleId' | 'description'>;

export interface AdcmUpgradeDetails extends AdcmDynamicActionDetails {
  bundle: {
    id: number;
    prototypeId: number;
    licenseStatus: AdcmLicenseStatus;
    unacceptedServicesPrototypes: AdcmUnacceptedServicesPrototype[];
  };
}

export type AdcmUpgradeRunConfig = AdcmDynamicActionRunConfig;
