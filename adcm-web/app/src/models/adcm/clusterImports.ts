import { AdcmClusterStatus } from '@models/adcm/cluster';

export enum AdcmClusterImportPayloadType {
  cluster = 'cluster',
  service = 'service',
}

export interface AdcmClusterImportService {
  id: number;
  name: string;
  displayName: string;
  version: string;
  isRequired: boolean;
  isMultiBind: boolean;
}

export interface AdcmClusterImportBind {
  id: number;
  source: {
    id: number;
    type: AdcmClusterImportPayloadType;
  };
}

export interface AdcmClusterImport {
  cluster: {
    id: number;
    name: string;
    status: AdcmClusterStatus;
    state: string;
  };
  importCluster: null | {
    id: number;
    isRequired: boolean;
    isMultiBind: boolean;
  };
  importServices: AdcmClusterImportService[] | null;
  binds: AdcmClusterImportBind[];
}

export interface AdcmClusterImportPostItem {
  id: number;
  type: AdcmClusterImportPayloadType;
}

export interface AdcmClusterImportPostPayload {
  source: AdcmClusterImportPostItem;
}

export interface AdcmClusterImportServiceFilter {
  serviceId: number | null;
}
