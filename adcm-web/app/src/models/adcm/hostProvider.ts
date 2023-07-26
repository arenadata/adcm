export interface AdcmHostProvider {
  id: number;
  name: string;
  prototype: AdcmHostProviderPrototype;
  state: string;
  description: string;
  concerns: AdcmHostProviderConcern[];
  isUpgradable: boolean;
  mainInfo: string;
}

export interface AdcmHostProviderPrototype {
  name: string;
  displayName: string;
  version: string;
  type: string;
}

export interface AdcmHostProviderConcern {
  id: number;
  reason: AdcmHostProviderReason;
  isBlocking: boolean;
}

export interface AdcmHostProviderReason {
  message: string;
  placeholder: AdcmHostProviderPlaceholder;
}

export interface AdcmHostProviderPlaceholder {
  source: AdcmHostProviderSource;
  target: AdcmHostProviderTarget;
}

export interface AdcmHostProviderSource {
  id: number;
  name: string;
  type: string;
}

export interface AdcmHostProviderTarget {
  id: number;
  name: string;
  type: string;
}

export interface AdcmHostProviderFilter {
  hostproviderName?: string;
  prototype?: string;
}

export interface AdcmHostProviderPayload {
  name: string;
  prototypeId: number;
  description: string;
}
