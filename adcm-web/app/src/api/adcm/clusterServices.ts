import type { AdcmService, Batch, AdcmServicesFilter } from '@models/adcm';
import { httpClient } from '@api/httpClient';
import qs from 'qs';
import { prepareQueryParams } from '@utils/apiUtils';
import { PaginationParams, SortParams } from '@models/table';

export class AdcmClusterServicesApi {
  public static async getClusterServices(
    clusterId: number,
    filter?: AdcmServicesFilter,
    sortParams?: SortParams,
    paginationParams?: PaginationParams,
  ) {
    const queryParams = prepareQueryParams(filter, sortParams, paginationParams);

    const query = qs.stringify(queryParams);
    const response = await httpClient.get<Batch<AdcmService>>(`/api/v2/clusters/${clusterId}/services?${query}`);
    return response.data;
  }

  public static async deleteClusterService(clusterId: number, servicesId: number) {
    await httpClient.delete(`/api/v2/clusters/${clusterId}/services/${servicesId}`);
  }
}
