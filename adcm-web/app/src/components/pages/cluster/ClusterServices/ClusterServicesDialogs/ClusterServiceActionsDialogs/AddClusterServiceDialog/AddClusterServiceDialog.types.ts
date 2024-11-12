import type { AdcmServicePrototype } from '@models/adcm';

export enum AddServiceStepKey {
  SelectServices = 'select_services',
  ServicesLicenses = 'service_license',
}

export interface AddClusterServicesFormData {
  clusterId: number | null;
  selectedServicesIds: number[];
  serviceCandidatesAcceptedLicense: Set<number>;
}

export interface AddClusterServicesStepProps {
  formData: AddClusterServicesFormData;
  onChange: (changes: Partial<AddClusterServicesFormData>) => void;
  unacceptedSelectedServices: AdcmServicePrototype[];
}
