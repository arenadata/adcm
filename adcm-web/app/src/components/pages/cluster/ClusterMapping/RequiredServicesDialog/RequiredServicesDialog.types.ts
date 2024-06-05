export enum RequiredServicesStepKey {
  ShowServices = 'show_services',
  ServicesLicenses = 'service_license',
}

export interface RequiredServicesFormData {
  serviceCandidatesAcceptedLicense: Set<number>;
}
