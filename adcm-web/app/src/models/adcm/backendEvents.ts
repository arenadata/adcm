import { AdcmConcerns } from './concern';
import { AdcmCluster } from './cluster';
import { AdcmHostProvider } from './hostProvider';
import { AdcmHost } from './host';
import { AdcmServiceComponent } from './clusterServiceComponent';
import { AdcmTask } from './jobs';
import { AdcmService } from './service';

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

// Task events

type JobTask = Omit<AdcmTask, 'id'>;

export type UpdateTaskEvent = {
  event: 'update_task';
  object: {
    id: number;
    changes: Partial<JobTask>;
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
  | UpdateTaskEvent;
