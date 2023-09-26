import qs from 'qs';
import type {
  AdcmHostProviderPayload,
  AdcmDynamicAction,
  Batch,
  AdcmDynamicActionDetails,
  AdcmDynamicActionRunConfig,
  AdcmHostProvider,
  AdcmHostProviderFilter,
} from '@models/adcm';
import { httpClient } from '@api/httpClient';
import { PaginationParams, SortParams } from '@models/table';
import { prepareQueryParams } from '@utils/apiUtils';

export class AdcmHostProvidersApi {
  public static async getHostProviders(
    filter: AdcmHostProviderFilter,
    sortParams?: SortParams,
    paginationParams?: PaginationParams,
  ) {
    const queryParams = prepareQueryParams(filter, sortParams, paginationParams);

    const query = qs.stringify(queryParams);
    const response = await httpClient.get<Batch<AdcmHostProvider>>(`/api/v2/hostproviders/?${query}`);
    return response.data;
  }

  public static async postHostProviders(payload: AdcmHostProviderPayload) {
    const mockPayload = {
      name: payload.name,
      prototypeId: payload.prototypeId,
      description: payload.description,
    };

    await httpClient.post('/api/v2/hostproviders/', mockPayload);
  }

  public static async deleteHostProvider(id: number) {
    await httpClient.delete(`/api/v2/hostproviders/${id}/`);
  }

  public static async getHostProvider(id: number) {
    const response = await httpClient.get<AdcmHostProvider>(`/api/v2/hostproviders/${id}/`);
    return response.data;
  }

  public static async getHostProviderActions(hostProviderId: number) {
    const response = await httpClient.get<AdcmDynamicAction[]>(`/api/v2/hostproviders/${hostProviderId}/actions/`);
    return response.data;
  }

  public static async getHostProviderActionsDetails(hostProviderId: number, actionId: number) {
    const response = await httpClient.get<AdcmDynamicActionDetails>(
      `/api/v2/hostproviders/${hostProviderId}/actions/${actionId}/`,
    );
    return response.data;
  }

  public static async runHostProviderAction(
    hostProviderId: number,
    actionId: number,
    actionRunConfig: AdcmDynamicActionRunConfig,
  ) {
    const response = await httpClient.post(
      `/api/v2/hostproviders/${hostProviderId}/actions/${actionId}/run/`,
      actionRunConfig,
    );

    return response.data;
  }
}
