import qs from 'qs';
import type { Batch } from '@models/adcm';
import { httpClient } from '@api/httpClient';
import { PaginationParams, SortParams } from '@models/table';
import { prepareQueryParams } from '@utils/apiUtils';
import { AdcmAuditOperationRequestParam, AdcmAuditOperation } from '@models/adcm';

export class AdcmAuditApi {
  public static async getAuditOperations(
    filter: AdcmAuditOperationRequestParam,
    sortParams: SortParams,
    paginationParams: PaginationParams,
  ) {
    const queryParams = prepareQueryParams(filter, sortParams, paginationParams);

    const query = qs.stringify(queryParams);
    const response = await httpClient.get<Batch<AdcmAuditOperation>>(`/api/v2/audit/operations/?${query}`);
    return response.data;
  }
}
