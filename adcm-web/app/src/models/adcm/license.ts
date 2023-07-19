export enum AdcmLicenseStatus {
  Accepted = 'accepted',
  Unaccepted = 'unaccepted',
}

export interface AdcmLicense {
  status: AdcmLicenseStatus;
  text?: string;
}
