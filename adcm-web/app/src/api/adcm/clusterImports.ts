import { httpClient } from '@api/httpClient';
import { AdcmClusterImport, AdcmClusterImportPostPayload, Batch } from '@models/adcm';
import { PaginationParams } from '@models/table';
import { prepareLimitOffset } from '@utils/apiUtils';
import qs from 'qs';

export class AdcmClusterImportsApi {
  public static async getClusterImports(clusterId: number, paginationParams: PaginationParams) {
    const query = qs.stringify(prepareLimitOffset(paginationParams));
    const response = await httpClient.get<Batch<AdcmClusterImport>>(`/api/v2/clusters/${clusterId}/imports/?${query}`);
    return response.data;
  }

  public static async postClusterImport(clusterId: number, importConfig: AdcmClusterImportPostPayload[]) {
    await httpClient.post(`/api/v2/clusters/${clusterId}/imports/`, importConfig);
  }
}
