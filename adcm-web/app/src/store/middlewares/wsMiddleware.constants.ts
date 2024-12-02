import { type ActionCreatorWithPayload, createAction } from '@reduxjs/toolkit';
import type {
  AdcmBackendEvent,
  CreateConcernEvent,
  CreateConfigEvent,
  DeleteConcernEvent,
  UpdateClusterEvent,
  UpdateComponentEvent,
  UpdateHostComponentMapEvent,
  UpdateHostEvent,
  UpdateHostProviderEvent,
  UpdateServiceEvent,
  UpdateJobEvent,
} from '@models/adcm';

export const wsActions = {
  create_adcm_config: createAction<CreateConfigEvent>('adcm/ws/create_adcm_config'),
  create_cluster_config: createAction<CreateConfigEvent>('adcm/ws/create_cluster_config'),
  create_service_config: createAction<CreateConfigEvent>('adcm/ws/create_service_config'),
  create_component_config: createAction<CreateConfigEvent>('adcm/ws/create_component_config'),
  create_hostprovider_config: createAction<CreateConfigEvent>('adcm/ws/create_hostprovider_config'),
  create_host_config: createAction<CreateConfigEvent>('adcm/ws/create_host_config'),

  create_adcm_concern: createAction<CreateConcernEvent>('adcm/ws/create_adcm_concern'),
  create_cluster_concern: createAction<CreateConcernEvent>('adcm/ws/create_cluster_concern'),
  create_service_concern: createAction<CreateConcernEvent>('adcm/ws/create_service_concern'),
  create_component_concern: createAction<CreateConcernEvent>('adcm/ws/create_component_concern'),
  create_hostprovider_concern: createAction<CreateConcernEvent>('adcm/ws/create_hostprovider_concern'),
  create_host_concern: createAction<CreateConcernEvent>('adcm/ws/create_host_concern'),

  delete_adcm_concern: createAction<DeleteConcernEvent>('adcm/ws/delete_adcm_concern'),
  delete_cluster_concern: createAction<DeleteConcernEvent>('adcm/ws/delete_cluster_concern'),
  delete_service_concern: createAction<DeleteConcernEvent>('adcm/ws/delete_service_concern'),
  delete_component_concern: createAction<DeleteConcernEvent>('adcm/ws/delete_component_concern'),
  delete_hostprovider_concern: createAction<DeleteConcernEvent>('adcm/ws/delete_hostprovider_concern'),
  delete_host_concern: createAction<DeleteConcernEvent>('adcm/ws/delete_host_concern'),

  update_cluster: createAction<UpdateClusterEvent>('adcm/ws/update_cluster'),
  update_service: createAction<UpdateServiceEvent>('adcm/ws/update_service'),
  update_component: createAction<UpdateComponentEvent>('adcm/ws/update_component'),
  update_hostprovider: createAction<UpdateHostProviderEvent>('adcm/ws/update_hostprovider'),
  update_host: createAction<UpdateHostEvent>('adcm/ws/update_host'),
  update_task: createAction<UpdateJobEvent>('adcm/ws/update_job'),
  update_hostcomponentmap: createAction<UpdateHostComponentMapEvent>('adcm/ws/update_hostcomponentmap'),
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
} satisfies { [key in AdcmBackendEvent['event']]: ActionCreatorWithPayload<any> };
