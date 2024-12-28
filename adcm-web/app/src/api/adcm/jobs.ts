import { httpClient } from '@api/httpClient';
import type { PaginationParams, SortParams } from '@models/table';
import type { Batch, AdcmJobsFilter, AdcmSubJobLogItem, AdcmJob, AdcmSubJobDetails } from '@models/adcm';
import qs from 'qs';
import { prepareQueryParams } from '@utils/apiUtils';

export class AdcmJobsApi {
  // Jobs (backend tasks)

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

  public static async stopJob(id: number) {
    await httpClient.post(`/api/v2/tasks/${id}/terminate/`);
  }

  // Sub jobs (backend jobs)

  public static async getSubJob(id: number) {
    const response = await httpClient.get<AdcmSubJobDetails>(`/api/v2/jobs/${id}/`);
    return response.data;
  }

  public static async getSubJobLog(id: number) {
    const response = await httpClient.get<AdcmSubJobLogItem[]>(`/api/v2/jobs/${id}/logs/`);
    return response.data;
  }

  public static async stopSubJob(id: number) {
    await httpClient.post(`/api/v2/jobs/${id}/terminate/`);
  }
}
