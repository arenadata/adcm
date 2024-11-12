import qs from 'qs';
import type { AdcmMaintenanceMode, Batch, CreateAdcmHostPayload, AdcmSetMaintenanceModeResponse } from '@models/adcm';
import type { PaginationParams, SortParams } from '@models/table';
import { httpClient } from '@api/httpClient';
import type { AdcmHost, AdcmHostsFilter, AdcmUpdatePayload } from '@models/adcm/host';
import { prepareQueryParams } from '@utils/apiUtils';
import type {
  AdcmDynamicAction,
  AdcmDynamicActionDetails,
  AdcmDynamicActionRunConfig,
} from '@models/adcm/dynamicAction';

export class AdcmHostsApi {
  public static async getHosts(filter?: AdcmHostsFilter, sortParams?: SortParams, paginationParams?: PaginationParams) {
    const queryParams = prepareQueryParams(filter, sortParams, paginationParams);

    const query = qs.stringify(queryParams);
    const response = await httpClient.get<Batch<AdcmHost>>(`/api/v2/hosts/?${query}`);
    return response.data;
  }

  public static async getHost(hostId: number) {
    const response = await httpClient.get<AdcmHost>(`/api/v2/hosts/${hostId}/`);
    return response.data;
  }

  public static async toggleMaintenanceMode(hostId: number, maintenanceMode: AdcmMaintenanceMode) {
    const response = await httpClient.post<AdcmSetMaintenanceModeResponse>(
      `/api/v2/hosts/${hostId}/maintenance-mode/`,
      {
        maintenanceMode,
      },
    );
    return response.data;
  }

  public static async deleteHost(id: number) {
    await httpClient.delete(`/api/v2/hosts/${id}/`);
  }

  public static async createHost(payload: CreateAdcmHostPayload) {
    await httpClient.post('/api/v2/hosts/', payload);
  }

  public static async getHostActions(hostId: number) {
    const query = qs.stringify({ is_host_own_action: true });
    const response = await httpClient.get<AdcmDynamicAction[]>(`/api/v2/hosts/${hostId}/actions/?${query}`);
    return response.data;
  }

  public static async getHostActionsDetails(hostId: number, actionId: number) {
    const response = await httpClient.get<AdcmDynamicActionDetails>(`/api/v2/hosts/${hostId}/actions/${actionId}/`);
    return response.data;
  }

  public static async runHostAction(hostId: number, actionId: number, actionRunConfig: AdcmDynamicActionRunConfig) {
    const response = await httpClient.post(`/api/v2/hosts/${hostId}/actions/${actionId}/run/`, actionRunConfig);

    return response.data;
  }

  public static async patchHost(hostId: number, payload: AdcmUpdatePayload) {
    await httpClient.patch(`/api/v2/hosts/${hostId}/`, payload);
  }
}
