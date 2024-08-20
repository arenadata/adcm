import { httpClient } from '@api/httpClient';
import type { AdcmDynamicAction, AdcmDynamicActionDetails, AdcmJob, Batch } from '@models/adcm';
import type {
  AdcmActionHostGroup,
  GetAdcmComponentActionHostGroupsArgs,
  GetAdcmComponentActionHostGroupArgs,
  CreateAdcmComponentActionHostGroupArgs,
  DeleteAdcmComponentActionHostGroupArgs,
  GetAdcmComponentActionHostGroupActionsArgs,
  GetAdcmComponentActionHostGroupActionArgs,
  RunAdcmComponentActionHostGroupActionArgs,
  GetAdcmComponentActionHostGroupsHostCandidatesArgs,
  AdcmActionHostGroupHost,
  GetAdcmComponentActionHostGroupHostCandidatesArgs,
  GetAdcmComponentActionHostGroupHostsArgs,
  AddAdcmComponentActionHostGroupHostArgs,
  DeleteAdcmComponentActionHostGroupHostArgs,
} from '@models/adcm/actionHostGroup';
import { prepareQueryParams } from '@utils/apiUtils';
import qs from 'qs';

export class AdcmClusterServiceComponentActionHostGroupsApi {
  // CRUD

  public static async getActionHostGroups(args: GetAdcmComponentActionHostGroupsArgs) {
    const { clusterId, serviceId, componentId, filter, paginationParams } = args;
    const queryParams = prepareQueryParams(filter, undefined, paginationParams);
    const query = qs.stringify(queryParams);

    const response = await httpClient.get<Batch<AdcmActionHostGroup>>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/components/${componentId}/action-host-groups/?${query}`,
    );

    return response.data;
  }

  public static async getActionHostGroup(args: GetAdcmComponentActionHostGroupArgs) {
    const { clusterId, serviceId, actionHostGroupId } = args;
    const response = await httpClient.get<AdcmActionHostGroup>(
      `/api/v2/clusters/${clusterId}/serviceId/${serviceId}/action-host-groups/${actionHostGroupId}/`,
    );

    return response.data;
  }

  public static async postActionHostGroup(args: CreateAdcmComponentActionHostGroupArgs) {
    const { clusterId, serviceId, componentId, actionHostGroup } = args;
    const response = await httpClient.post<AdcmActionHostGroup>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/components/${componentId}/action-host-groups/`,
      actionHostGroup,
    );

    return response.data;
  }

  public static async deleteActionHostGroup(args: DeleteAdcmComponentActionHostGroupArgs) {
    const { clusterId, serviceId, componentId, actionHostGroupId } = args;
    await httpClient.delete(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/components/${componentId}/action-host-groups/${actionHostGroupId}/`,
    );
  }

  // Actions

  public static async getActionHostGroupActions(args: GetAdcmComponentActionHostGroupActionsArgs) {
    const { clusterId, serviceId, componentId, actionHostGroupId, sortParams, filter, paginationParams } = args;
    const queryParams = prepareQueryParams(filter, sortParams, paginationParams);
    const query = qs.stringify(queryParams);

    const response = await httpClient.get<AdcmDynamicAction[]>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/components/${componentId}/action-host-groups/${actionHostGroupId}/actions/?${query}`,
    );

    return response.data;
  }

  public static async getActionHostGroupAction(args: GetAdcmComponentActionHostGroupActionArgs) {
    const { clusterId, serviceId, componentId, actionHostGroupId, actionId } = args;
    const response = await httpClient.get<AdcmDynamicActionDetails>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/components/${componentId}/action-host-groups/${actionHostGroupId}/actions/${actionId}/`,
    );

    return response.data;
  }

  public static async postActionHostGroupAction(args: RunAdcmComponentActionHostGroupActionArgs) {
    const { clusterId, serviceId, componentId, actionHostGroupId, actionId, actionRunConfig } = args;
    const response = await httpClient.post<AdcmJob>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/components/${componentId}/action-host-groups/${actionHostGroupId}/actions/${actionId}/run/`,
      actionRunConfig,
    );

    return response.data;
  }

  // Host candidates

  public static async getActionHostGroupsHostCandidates(args: GetAdcmComponentActionHostGroupsHostCandidatesArgs) {
    const { clusterId, serviceId, componentId, filter } = args;
    const queryParams = prepareQueryParams(filter);
    const query = qs.stringify(queryParams);

    const response = await httpClient.get<AdcmActionHostGroupHost[]>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/components/${componentId}/action-host-groups/host-candidates/?${query}`,
    );

    return response.data;
  }

  public static async getActionHostGroupHostCandidates(args: GetAdcmComponentActionHostGroupHostCandidatesArgs) {
    const { clusterId, serviceId, componentId, actionHostGroupId, filter } = args;
    const queryParams = prepareQueryParams(filter);
    const query = qs.stringify(queryParams);

    const response = await httpClient.get<AdcmActionHostGroupHost[]>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/components/${componentId}/action-host-groups/${actionHostGroupId}/host-candidates/?${query}`,
    );

    return response.data;
  }

  // Hosts

  public static async getActionHostGroupHosts(args: GetAdcmComponentActionHostGroupHostsArgs) {
    const { clusterId, serviceId, componentId, actionHostGroupId, sortParams, paginationParams } = args;
    const queryParams = prepareQueryParams(undefined, sortParams, paginationParams);
    const query = qs.stringify(queryParams);

    const response = await httpClient.get<Batch<AdcmActionHostGroupHost>>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/components/${componentId}/action-host-groups/${actionHostGroupId}/hosts/?${query}`,
    );

    return response.data;
  }

  public static async postActionHostGroupHost(args: AddAdcmComponentActionHostGroupHostArgs) {
    const { clusterId, serviceId, componentId, actionHostGroupId, hostId } = args;
    const response = await httpClient.post<AdcmActionHostGroupHost>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/components/${componentId}/action-host-groups/${actionHostGroupId}/hosts/`,
      { hostId },
    );

    return response.data;
  }

  public static async deleteActionHostGroupHost(args: DeleteAdcmComponentActionHostGroupHostArgs) {
    const { clusterId, serviceId, componentId, actionHostGroupId, hostId } = args;
    await httpClient.delete(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/components/${componentId}/action-host-groups/${actionHostGroupId}/hosts/${hostId}/`,
    );
  }
}
