import type { AdcmLicense, AdcmLicenseStatus } from '@models/adcm/license';
import type { AdcmBundleRelated, AdcmContractVersionStatus } from '@models/adcm/bundle';

export interface AdcmPrototypeVersion {
  id: number;
  version: string;
  licenseStatus: AdcmLicenseStatus;
  bundle: AdcmBundleRelated;
}

export interface AdcmPrototypeVersionsFilter {
  type: AdcmPrototypeType;
  contractVersionStatus?: AdcmContractVersionStatus;
  contractVersionValue?: string;
}

export interface AdcmPrototypeVersions {
  name: string;
  displayName: string;
  versions: AdcmPrototypeVersion[];
}

export enum AdcmPrototypeType {
  Adcm = 'adcm',
  Cluster = 'cluster',
  Service = 'service',
  Component = 'component',
  Provider = 'provider',
  Host = 'host',
}

export interface AdcmPrototypesFilter {
  bundleId?: number;
  type?: AdcmPrototypeType;
  ids?: number[];
  contractVersionStatus?: AdcmContractVersionStatus;
  contractVersionValue?: string;
}

export interface AdcmPrototype {
  id: number;
  name: string;
  displayName: string;
  description?: string;
  type: AdcmPrototypeType;
  version: string;
  bundleId: number;
  bundle?: AdcmBundleRelated;
  license: AdcmLicense;
}

export interface AdcmProduct {
  name: string;
  displayName: string;
}

export interface AdcmPrototypeShortView {
  id: number;
  name: string;
  displayName: string;
  version: string;
}
