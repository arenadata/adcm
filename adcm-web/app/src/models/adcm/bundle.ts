export enum AdcmBundleSignatureStatus {
  Verified = 'verified',
  NotVerified = 'not verified',
}

export interface AdcmBundlesFilter {
  displayName?: string;
  product?: string;
}

export interface AdcmBundle {
  id: number;
  name: string;
  displayName: string;
  version: string;
  edition?: string;
  uploadTime: string;
  signatureStatus: AdcmBundleSignatureStatus;
  category?: number;
}
