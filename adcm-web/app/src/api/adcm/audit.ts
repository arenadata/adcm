import qs from 'qs';
import type {
  AdcmAuditLogin,
  AdcmAuditLoginRequestParam,
  AdcmAuditOperationRequestParam,
  AdcmAuditOperation,
  Batch,
} from '@models/adcm';
import { httpClient } from '@api/httpClient';
import type { PaginationParams, SortParams } from '@models/table';
import { prepareQueryParams } from '@utils/apiUtils';

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

  public static async getAuditLogins(
    filter: AdcmAuditLoginRequestParam,
    sortParams: SortParams,
    paginationParams: PaginationParams,
  ) {
    const queryParams = prepareQueryParams(filter, sortParams, paginationParams);

    const query = qs.stringify(queryParams);
    const response = await httpClient.get<Batch<AdcmAuditLogin>>(`/api/v2/audit/logins/?${query}`);
    return response.data;
  }
}
