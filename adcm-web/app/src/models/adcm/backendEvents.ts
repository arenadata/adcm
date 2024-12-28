import type { AdcmConcerns } from './concern';
import type { AdcmCluster } from './cluster';
import type { AdcmHostProvider } from './hostProvider';
import type { AdcmHost } from './host';
import type { AdcmServiceComponent } from './clusterServiceComponent';
import type { AdcmJob } from './jobs';
import type { AdcmService } from './service';

// Config events

export type CreateConfigEvent = {
  event:
    | 'create_adcm_config'
    | 'create_cluster_config'
    | 'create_service_config'
    | 'create_component_config'
    | 'create_hostprovider_config'
    | 'create_host_config';
  object: {
    id: number;
  };
};

// Concern events

export type CreateConcernEvent = {
  event:
    | 'create_adcm_concern'
    | 'create_cluster_concern'
    | 'create_service_concern'
    | 'create_component_concern'
    | 'create_hostprovider_concern'
    | 'create_host_concern';
  object: {
    // the concrete entity id, e.g. clusterId
    id: number;
    changes: AdcmConcerns;
  };
};

export type DeleteConcernEvent = {
  event:
    | 'delete_adcm_concern'
    | 'delete_cluster_concern'
    | 'delete_service_concern'
    | 'delete_component_concern'
    | 'delete_hostprovider_concern'
    | 'delete_host_concern';
  object: {
    id: number;
    changes: {
      id: number;
    };
  };
};

// Host component map events

export type UpdateHostComponentMapEvent = {
  event: 'update_hostcomponentmap';
  object: {
    id: number;
  };
};

// Cluster events

type ClusterChanges = Omit<AdcmCluster, 'id'>;

export type UpdateClusterEvent = {
  event: 'update_cluster';
  object: {
    id: number;
    changes: Partial<ClusterChanges>;
  };
};

// Service events

type ServiceChanges = Omit<AdcmService, 'id'>;

export type UpdateServiceEvent = {
  event: 'update_service';
  object: {
    id: number;
    changes: Partial<ServiceChanges>;
  };
};

// Component events

type ComponentChanges = Omit<AdcmServiceComponent, 'id'>;

export type UpdateComponentEvent = {
  event: 'update_component';
  object: {
    id: number;
    changes: Partial<ComponentChanges>;
  };
};

// Host provider events

type HostProviderChanges = Omit<AdcmHostProvider, 'id'>;

export type UpdateHostProviderEvent = {
  event: 'update_hostprovider';
  object: {
    id: number;
    changes: Partial<HostProviderChanges>;
  };
};

// Host events

type HostChanges = Omit<AdcmHost, 'id'>;

export type UpdateHostEvent = {
  event: 'update_host';
  object: {
    id: number;
    changes: Partial<HostChanges>;
  };
};

// Job (Task) events

type JobChanges = Omit<AdcmJob, 'id'>;

export type UpdateJobEvent = {
  event: 'update_task'; // <-- backend sends `update_task`, so we cann't change here to update_job
  object: {
    id: number;
    changes: Partial<JobChanges>;
  };
};

export type AdcmBackendEvent =
  | CreateConfigEvent
  | CreateConcernEvent
  | DeleteConcernEvent
  | UpdateHostComponentMapEvent
  | UpdateClusterEvent
  | UpdateServiceEvent
  | UpdateComponentEvent
  | UpdateHostProviderEvent
  | UpdateHostEvent
  | UpdateJobEvent;
