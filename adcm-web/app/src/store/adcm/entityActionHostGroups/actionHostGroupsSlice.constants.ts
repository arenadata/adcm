import {
  AdcmClusterActionHostGroupsApi,
  AdcmClusterServiceActionHostGroupsApi,
  AdcmClusterServiceComponentActionHostGroupsApi,
} from '@api';
import type { ActionHostGroupApi, ActionHostGroupOwner } from './actionHostGroups.types';

export const services: { [owner in ActionHostGroupOwner]: ActionHostGroupApi } = {
  cluster: AdcmClusterActionHostGroupsApi,
  service: AdcmClusterServiceActionHostGroupsApi,
  component: AdcmClusterServiceComponentActionHostGroupsApi,
};
