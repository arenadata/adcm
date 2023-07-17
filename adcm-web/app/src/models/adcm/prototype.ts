export interface AdcmPrototypeVersion {
  id: number;
  version: string;
  isLicenseAccepted: boolean;
  bundleId: number;
}

export interface AdcmPrototypeVersionsFilter {
  type: PrototypeType;
}

export interface AdcmPrototypeVersions {
  name: string;
  versions: AdcmPrototypeVersion[];
}

export enum PrototypeType {
  Adcm = 'adcm',
  Cluster = 'cluster',
  Service = 'service',
  Component = 'component',
  Provider = 'provider',
  Host = 'host',
}
