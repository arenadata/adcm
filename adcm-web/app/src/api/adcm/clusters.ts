import { httpClient } from '@api/httpClient';
import { PaginationParams, SortParams } from '@models/table';
import {
  Batch,
  AdcmClustersFilter,
  AdcmCluster,
  CreateAdcmClusterPayload,
  RenameAdcmClusterPayload,
  AdcmUpgradeRunConfig,
  AdcmUpgradeShort,
  AdcmUpgradeDetails,
} from '@models/adcm';
import qs from 'qs';
import { prepareQueryParams } from '@utils/apiUtils';
import { AdcmDynamicAction, AdcmDynamicActionDetails, AdcmDynamicActionRunConfig } from '@models/adcm/dynamicAction';

export class AdcmClustersApi {
  public static async getClusters(
    filter?: AdcmClustersFilter,
    sortParams?: SortParams,
    paginationParams?: PaginationParams,
  ) {
    const queryParams = prepareQueryParams(filter, sortParams, paginationParams);

    const query = qs.stringify(queryParams);
    const response = await httpClient.get<Batch<AdcmCluster>>(`/api/v2/clusters/?${query}`);
    return response.data;
  }

  public static async postCluster(payload: CreateAdcmClusterPayload) {
    const mockPayload = {
      name: payload.name,
      description: payload.description,
      prototypeId: payload.prototypeId,
    };

    await httpClient.post('/api/v2/clusters/', mockPayload);
  }

  public static async getCluster(clusterId: number) {
    const response = await httpClient.get<AdcmCluster>(`/api/v2/clusters/${clusterId}/`);
    return response.data;
  }

  public static async patchCluster(clusterId: number, payload: RenameAdcmClusterPayload) {
    await httpClient.patch(`/api/v2/clusters/${clusterId}/`, payload);
  }

  public static async deleteCluster(clusterId: number) {
    await httpClient.delete(`/api/v2/clusters/${clusterId}/`);
  }

  public static async getClusterUpgrades(clusterId: number) {
    const response = await httpClient.get<AdcmUpgradeShort[]>(`/api/v2/clusters/${clusterId}/upgrades/`);
    return response.data;
  }

  public static async getClusterUpgrade(clusterId: number, upgradeId: number) {
    const response = await httpClient.get<AdcmUpgradeDetails>(`/api/v2/clusters/${clusterId}/upgrades/${upgradeId}/`);
    return response.data;
  }

  public static async getClusterActions(clusterId: number) {
    const response = await httpClient.get<AdcmDynamicAction[]>(`/api/v2/clusters/${clusterId}/actions/`);
    return response.data;
  }

  public static async getClusterActionDetails(clusterId: number, actionId: number) {
    const response = await httpClient.get<AdcmDynamicActionDetails>(
      `/api/v2/clusters/${clusterId}/actions/${actionId}/`,
    );
    return response.data;
  }

  public static async runClusterAction(
    clusterId: number,
    actionId: number,
    actionRunConfig: AdcmDynamicActionRunConfig,
  ) {
    const response = await httpClient.post(`/api/v2/clusters/${clusterId}/actions/${actionId}/run/`, actionRunConfig);

    return response.data;
  }

  public static async runClusterUpgrade(clusterId: number, upgradeId: number, upgradeRunConfig: AdcmUpgradeRunConfig) {
    const response = await httpClient.post(
      `/api/v2/clusters/${clusterId}/upgrades/${upgradeId}/run/`,
      upgradeRunConfig,
    );

    return response.data;
  }

  public static async linkHost(clusterId: number, hostIds: number[]) {
    const hostIdsPayload = hostIds.map((id) => ({ hostId: id }));
    await httpClient.post(`/api/v2/clusters/${clusterId}/hosts/`, hostIdsPayload);
  }

  public static async unlinkHost(clusterId: number, hostId: number) {
    await httpClient.delete(`/api/v2/clusters/${clusterId}/hosts/${hostId}/`);
  }
}
