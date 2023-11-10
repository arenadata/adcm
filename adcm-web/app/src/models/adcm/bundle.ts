import { AdcmPrototype } from '.';

export enum AdcmBundleSignatureStatus {
  Valid = 'valid',
  Invalid = 'invalid',
  Absent = 'absent',
}

export interface AdcmBundlesFilter {
  displayName?: string;
  product?: string;
}

export interface AdcmBundleMainPrototype extends AdcmPrototype, Omit<AdcmPrototype, 'bundleId'> {}

export interface AdcmBundle {
  id: number;
  name: string;
  displayName: string;
  version: string;
  edition?: string;
  mainPrototype: AdcmBundleMainPrototype;
  uploadTime: string;
  signatureStatus: AdcmBundleSignatureStatus;
  category?: number;
}
