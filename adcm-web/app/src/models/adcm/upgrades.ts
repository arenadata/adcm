import type { AdcmPrototype } from './prototype';
import type { AdcmDynamicActionDetails, AdcmDynamicActionRunConfig } from './dynamicAction';
import type { AdcmLicenseStatus } from './license';

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
