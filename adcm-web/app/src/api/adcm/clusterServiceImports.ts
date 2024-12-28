import { httpClient } from '@api/httpClient';
import type { AdcmClusterImport, AdcmClusterImportPostPayload, Batch } from '@models/adcm';
import type { PaginationParams } from '@models/table';
import { prepareLimitOffset } from '@utils/apiUtils';
import qs from 'qs';

export class AdcmClusterServiceImportsApi {
  public static async getClusterServiceImports(
    clusterId: number,
    serviceId: number,
    paginationParams: PaginationParams,
  ) {
    const query = qs.stringify(prepareLimitOffset(paginationParams));

    const response = await httpClient.get<Batch<AdcmClusterImport>>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/imports/?${query}`,
    );

    return response.data;
  }

  public static async postClusterServiceImport(
    clusterId: number,
    serviceId: number,
    importConfig: AdcmClusterImportPostPayload[],
  ) {
    await httpClient.post(`/api/v2/clusters/${clusterId}/services/${serviceId}/imports/`, importConfig);
  }
}
