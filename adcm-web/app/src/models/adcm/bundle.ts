import type { AdcmPrototype } from './prototype';

export enum AdcmBundleSignatureStatus {
  Valid = 'valid',
  Invalid = 'invalid',
  Absent = 'absent',
}

export enum AdcmContractVersionStatus {
  Supported = 'supported',
  Deprecated = 'deprecated',
  Unsupported = 'unsupported',
}

export interface AdcmContractVersion {
  status: AdcmContractVersionStatus;
  value: string;
}

export interface AdcmBundleRelated {
  id: number;
  edition: string;
  contractVersion: AdcmContractVersion;
}

export interface AdcmBundlesFilter {
  displayName?: string;
  product?: string;
  contractVersionStatus?: AdcmContractVersionStatus;
  contractVersionValue?: string;
}

export interface AdcmBundleMainPrototype extends AdcmPrototype, Omit<AdcmPrototype, 'bundleId'> {}

export interface AdcmBundle {
  id: number;
  name: string;
  displayName: string;
  version: string;
  edition?: string;
  contractVersion: AdcmContractVersion;
  mainPrototype: AdcmBundleMainPrototype;
  uploadTime: string;
  signatureStatus: AdcmBundleSignatureStatus;
  category?: number;
}

export interface AdcmBundleShort {
  id: number;
  name: string;
  displayName: string;
  version: string;
  edition: string;
}
