export interface AdcmPrototypeVersion {
  id: number;
  version: string;
  isLicenseAccepted: boolean;
  bundleId: number;
}

export interface AdcmPrototypeVersions {
  name: string;
  versions: AdcmPrototypeVersion[];
}
