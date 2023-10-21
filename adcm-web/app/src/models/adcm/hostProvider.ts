import { AdcmConcerns } from '@models/adcm/concern';

export interface AdcmHostProvider {
  id: number;
  name: string;
  prototype: AdcmHostProviderPrototype;
  state: string;
  multiState: string[];
  description: string;
  concerns: AdcmConcerns[];
  isUpgradable: boolean;
  mainInfo: string;
}

export interface AdcmHostProviderPrototype {
  id: number;
  name: string;
  displayName: string;
  version: string;
}

export interface AdcmHostProviderFilter {
  name?: string;
  prototypeDisplayName?: string;
}

export interface AdcmHostProviderPayload {
  name: string;
  prototypeId: number;
  description: string;
}
