export enum AdcmClusterStatus {
  Up = 'UP',
  Down = 'DOWN',
}

export interface AdcmClusterConcernReason {
  message: string;
  placeholder: {
    source: {
      id: number;
      name: string;
      type: string;
    };
    target: {
      id: number;
      name: string;
      type: string;
    };
  };
}

export interface AdcmClusterConcern {
  id: number;
  reason: AdcmClusterConcernReason;
  isBlocking: boolean;
}

export interface AdcmCluster {
  id: number;
  name: string;
  state: string;
  multiState: string[];
  status: AdcmClusterStatus;
  prototypeName: string;
  prototypeVersion: string;
  description: string;
  concerns: AdcmClusterConcern[];
  isUpgradable: boolean;
  mainInfo: string;
}

export interface AdcmClustersFilter {
  clusterName?: string;
  clusterStatus?: AdcmClusterStatus;
  prototypeName?: string;
}

export interface CreateAdcmClusterPayload {
  isLicenseAccepted: boolean;
  prototypeId: number;
  name: string;
  description: string;
}

export interface UpdateAdcmClusterPayload {
  name: string;
}
