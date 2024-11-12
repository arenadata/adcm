import type { PaginationParams, SortParams } from '@models/table';
import type { AdcmDynamicActionRunConfig } from './dynamicAction';

export interface AdcmActionHostGroup {
  id: number;
  name: string;
  description: string;
  hosts: AdcmActionHostGroupHost[];
}

export interface AdcmActionHostGroupsFilter {
  name?: string;
  hasHost?: string;
}

export interface AdcmActionHostGroupsActionsFilter {
  hasHost?: string;
  isHostOwnAction?: boolean;
  name?: string;
  displayName?: string;
  prototypeId?: number;
}

export interface AdcmActionHostGroupsHostCandidatesFilter {
  name?: string;
  hasHost?: string;
}

export interface AdcmActionHostGroupHost {
  id: number;
  name: string;
}

export interface NewAdcmActionHostGroup {
  name: string;
  description?: string;
}

// Cluster Action Host Groups

// CRUD
export interface GetAdcmClusterActionHostGroupsArgs {
  clusterId: number;
  filter: AdcmActionHostGroupsFilter;
  paginationParams: PaginationParams;
}

export interface GetAdcmClusterActionHostGroupArgs {
  clusterId: number;
  actionHostGroupId: number;
}

export interface CreateAdcmClusterActionHostGroupArgs {
  clusterId: number;
  actionHostGroup: NewAdcmActionHostGroup;
}

export interface DeleteAdcmClusterActionHostGroupArgs {
  clusterId: number;
  actionHostGroupId: number;
}

// Actions
export interface GetAdcmClusterActionHostGroupActionsArgs {
  clusterId: number;
  actionHostGroupId: number;
  sortParams?: SortParams;
  paginationParams?: PaginationParams;
  filter?: AdcmActionHostGroupsActionsFilter;
}

export interface GetAdcmClusterActionHostGroupActionArgs {
  clusterId: number;
  actionHostGroupId: number;
  actionId: number;
}

export interface RunAdcmClusterActionHostGroupActionArgs {
  clusterId: number;
  actionHostGroupId: number;
  actionId: number;
  actionRunConfig: AdcmDynamicActionRunConfig;
}

// Hosts candidates
export interface GetAdcmClusterActionHostGroupsHostCandidatesArgs {
  clusterId: number;
  filter: AdcmActionHostGroupsHostCandidatesFilter;
}

export interface GetAdcmClusterActionHostGroupHostCandidatesArgs {
  clusterId: number;
  actionHostGroupId: number;
  filter: AdcmActionHostGroupsHostCandidatesFilter;
}

//Hosts
export interface GetAdcmClusterActionHostGroupHostsArgs {
  clusterId: number;
  actionHostGroupId: number;
  paginationParams?: PaginationParams;
  sortParams?: SortParams;
}

export interface AddAdcmClusterActionHostGroupHostArgs {
  clusterId: number;
  actionHostGroupId: number;
  hostId: number;
}

export interface DeleteAdcmClusterActionHostGroupHostArgs {
  clusterId: number;
  actionHostGroupId: number;
  hostId: number;
}

// Service Action Host Groups

// CRUD
export interface GetAdcmServiceActionHostGroupsArgs {
  clusterId: number;
  serviceId: number;
  filter: AdcmActionHostGroupsFilter;
  paginationParams: PaginationParams;
}

export interface GetAdcmServiceActionHostGroupArgs {
  clusterId: number;
  serviceId: number;
  actionHostGroupId: number;
}

export interface CreateAdcmServiceActionHostGroupArgs {
  clusterId: number;
  serviceId: number;
  actionHostGroup: NewAdcmActionHostGroup;
}

export interface DeleteAdcmServiceActionHostGroupArgs {
  clusterId: number;
  serviceId: number;
  actionHostGroupId: number;
}

// Actions
export interface GetAdcmServiceActionHostGroupActionsArgs {
  clusterId: number;
  serviceId: number;
  actionHostGroupId: number;
  sortParams: SortParams;
  paginationParams: PaginationParams;
  filter: AdcmActionHostGroupsActionsFilter;
}

export interface GetAdcmServiceActionHostGroupActionArgs {
  clusterId: number;
  serviceId: number;
  actionHostGroupId: number;
  actionId: number;
}

export interface RunAdcmServiceActionHostGroupActionArgs {
  clusterId: number;
  serviceId: number;
  actionHostGroupId: number;
  actionId: number;
  actionRunConfig: AdcmDynamicActionRunConfig;
}

// Hosts candidates
export interface GetAdcmServiceActionHostGroupsHostCandidatesArgs {
  clusterId: number;
  serviceId: number;
  filter: AdcmActionHostGroupsHostCandidatesFilter;
}

export interface GetAdcmServiceActionHostGroupHostCandidatesArgs {
  clusterId: number;
  serviceId: number;
  actionHostGroupId: number;
  filter: AdcmActionHostGroupsHostCandidatesFilter;
}

// Hosts
export interface GetAdcmServiceActionHostGroupHostsArgs {
  clusterId: number;
  serviceId: number;
  actionHostGroupId: number;
  paginationParams?: PaginationParams;
  sortParams?: SortParams;
}

export interface AddAdcmServiceActionHostGroupHostArgs {
  clusterId: number;
  serviceId: number;
  actionHostGroupId: number;
  hostId: number;
}

export interface DeleteAdcmServiceActionHostGroupHostArgs {
  clusterId: number;
  serviceId: number;
  actionHostGroupId: number;
  hostId: number;
}

// Component Action Host Groups

// CRUD
export interface GetAdcmComponentActionHostGroupsArgs {
  clusterId: number;
  serviceId: number;
  componentId: number;
  filter: AdcmActionHostGroupsFilter;
  paginationParams: PaginationParams;
}

export interface GetAdcmComponentActionHostGroupArgs {
  clusterId: number;
  serviceId: number;
  componentId: number;
  actionHostGroupId: number;
}

export interface CreateAdcmComponentActionHostGroupArgs {
  clusterId: number;
  serviceId: number;
  componentId: number;
  actionHostGroup: NewAdcmActionHostGroup;
}

export interface DeleteAdcmComponentActionHostGroupArgs {
  clusterId: number;
  serviceId: number;
  componentId: number;
  actionHostGroupId: number;
}

// Actions
export interface GetAdcmComponentActionHostGroupActionsArgs {
  clusterId: number;
  serviceId: number;
  componentId: number;
  actionHostGroupId: number;
  sortParams: SortParams;
  paginationParams: PaginationParams;
  filter: AdcmActionHostGroupsActionsFilter;
}

export interface GetAdcmComponentActionHostGroupActionArgs {
  clusterId: number;
  serviceId: number;
  componentId: number;
  actionHostGroupId: number;
  actionId: number;
}

export interface RunAdcmComponentActionHostGroupActionArgs {
  clusterId: number;
  serviceId: number;
  componentId: number;
  actionHostGroupId: number;
  actionId: number;
  actionRunConfig: AdcmDynamicActionRunConfig;
}

// Hosts candidates
export interface GetAdcmComponentActionHostGroupsHostCandidatesArgs {
  clusterId: number;
  serviceId: number;
  componentId: number;
  actionHostGroupId: number;
  filter: AdcmActionHostGroupsHostCandidatesFilter;
}

export interface GetAdcmComponentActionHostGroupHostCandidatesArgs {
  clusterId: number;
  serviceId: number;
  componentId: number;
  actionHostGroupId: number;
  filter: AdcmActionHostGroupsHostCandidatesFilter;
}

// Hosts
export interface GetAdcmComponentActionHostGroupHostsArgs {
  clusterId: number;
  serviceId: number;
  componentId: number;
  actionHostGroupId: number;
  paginationParams?: PaginationParams;
  sortParams?: SortParams;
}

export interface AddAdcmComponentActionHostGroupHostArgs {
  clusterId: number;
  serviceId: number;
  componentId: number;
  actionHostGroupId: number;
  hostId: number;
}

export interface DeleteAdcmComponentActionHostGroupHostArgs {
  clusterId: number;
  serviceId: number;
  componentId: number;
  actionHostGroupId: number;
  hostId: number;
}
