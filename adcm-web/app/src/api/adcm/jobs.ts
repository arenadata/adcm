import { httpClient } from '@api/httpClient';
import { PaginationParams, SortParams } from '@models/table';
import { Batch, AdcmJobsFilter, AdcmJob, AdcmJobLogItem, AdcmTask } from '@models/adcm';
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
    const response = await httpClient.get<AdcmJob>(`/api/v2/jobs/${id}/`);
    return response.data;
  }

  public static async getJobLog(id: number) {
    const response = await httpClient.get<AdcmJobLogItem[]>(`/api/v2/jobs/${id}/logs/`);
    return response.data;
  }

  public static async getTask(id: number) {
    const response = await httpClient.get<AdcmTask>(`/api/v2/tasks/${id}/`);
    return response.data;
  }

  public static async stopJob(id: number) {
    await httpClient.post(`/api/v2/tasks/${id}/terminate/`);
  }

  public static async stopChildJob(childJobId: number) {
    await httpClient.post(`/api/v2/jobs/${childJobId}/terminate/`);
  }
}
