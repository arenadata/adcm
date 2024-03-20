export enum AdcmLicenseStatus {
  Accepted = 'accepted',
  Unaccepted = 'unaccepted',
  Absent = 'absent',
}

export interface AdcmLicense {
  status: AdcmLicenseStatus;
  text: string | null;
}
