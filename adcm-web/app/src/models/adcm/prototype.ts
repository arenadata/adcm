import type { AdcmLicense, AdcmLicenseStatus } from '@models/adcm/license';

export interface AdcmPrototypeVersion {
  id: number;
  version: string;
  licenseStatus: AdcmLicenseStatus;
  bundle: {
    id: number;
    edition: string;
  };
}

export interface AdcmPrototypeVersionsFilter {
  type: AdcmPrototypeType;
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
}

export interface AdcmPrototype {
  id: number;
  name: string;
  displayName: string;
  description?: string;
  type: AdcmPrototypeType;
  version: string;
  bundleId: number;
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
