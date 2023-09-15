import qs from 'qs';
import type { AdcmMaintenanceMode, Batch, CreateAdcmHostPayload } from '@models/adcm';
import { PaginationParams, SortParams } from '@models/table';
import { httpClient } from '@api/httpClient';
import { AdcmHost, AdcmHostsFilter } from '@models/adcm/host';
import { prepareQueryParams } from '@utils/apiUtils';
import { AdcmDynamicAction, AdcmDynamicActionDetails, AdcmDynamicActionRunConfig } from '@models/adcm/dynamicAction';

export class AdcmHostsApi {
  public static async getHosts(filter?: AdcmHostsFilter, sortParams?: SortParams, paginationParams?: PaginationParams) {
    const queryParams = prepareQueryParams(filter, sortParams, paginationParams);

    const query = qs.stringify(queryParams);
    const response = await httpClient.get<Batch<AdcmHost>>(`/api/v2/hosts/?${query}`);
    return response.data;
  }

  public static async toggleMaintenanceMode(hostId: number, maintenanceMode: AdcmMaintenanceMode) {
    await httpClient.post(`/api/v2/hosts/${hostId}/maintenance-mode/`, { maintenanceMode });
  }

  public static async deleteHost(id: number) {
    await httpClient.delete(`/api/v2/hosts/${id}/`);
  }

  public static async createHost(payload: CreateAdcmHostPayload) {
    await httpClient.post('/api/v2/hosts/', payload);
  }

  public static async getHostActions(hostId: number) {
    const response = await httpClient.get<AdcmDynamicAction[]>(`/api/v2/hosts/${hostId}/actions/`);
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
}
