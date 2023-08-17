import { httpClient } from '@api/httpClient';
import { PaginationParams, SortParams } from '@models/table';
import { Batch, AdcmJobsFilter, AdcmJob } from '@models/adcm';
import qs from 'qs';
import { prepareQueryParams } from '@utils/apiUtils';

export class AdcmJobsApi {
  public static async getJobs(filter: AdcmJobsFilter, sortParams?: SortParams, paginationParams?: PaginationParams) {
    const queryParams = prepareQueryParams(filter, sortParams, paginationParams);

    const query = qs.stringify(queryParams);
    const response = await httpClient.get<Batch<AdcmJob>>(`/api/v2/tasks/?${query}`);
    return response.data;
  }

  public static async getJob(id: number) {
    const response = await httpClient.get<AdcmJob>(`/api/v2/tasks/${id}/`);
    return response.data;
  }

  public static async restartJob(id: number) {
    await httpClient.post(`/api/v2/tasks/${id}/restart`);
  }
}
