export interface AdcmActionHostGroupHost {
  id: number;
  name: string;
}

export interface AddAdcmActionHostGroupHostPayload {
  hostId: number;
}

export interface AdcmActionHostGroup {
  id: number;
  name: string;
  description: string;
  hosts: AdcmActionHostGroupHost[];
}

export interface CreateAdcmActionHostGroupPayload {
  name: string;
  description?: string;
}

export interface AdcmActionHostGroupsActionsFilter {
  displayName?: string;
  isHostOwnAction?: boolean;
  name?: string;
  prototypeId?: number;
}
