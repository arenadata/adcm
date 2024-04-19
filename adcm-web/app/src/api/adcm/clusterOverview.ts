import { httpClient } from '@api/httpClient';
import {
  AdcmClusterOverviewStatusHost,
  AdcmClusterOverviewStatusService,
  AdcmHostStatus,
  AdcmServiceStatus,
  Batch,
} from '@models/adcm';
import { PaginationParams } from '@models/table';
import { prepareLimitOffset } from '@utils/apiUtils';
import qs from 'qs';

export class AdcmClusterOverviewApi {
  public static async getClusterServicesStatuses(
    clusterId: number,
    paginationParams: PaginationParams,
    status?: AdcmServiceStatus,
  ) {
    const query = qs.stringify({
      ...prepareLimitOffset(paginationParams),
      status,
    });
    const response = await httpClient.get<Batch<AdcmClusterOverviewStatusService>>(
      `/api/v2/clusters/${clusterId}/statuses/services/?${query}`,
    );

    return response.data;
  }

  public static async getClusterHostsStatuses(
    clusterId: number,
    paginationParams: PaginationParams,
    status?: AdcmHostStatus,
  ) {
    const query = qs.stringify({
      ...prepareLimitOffset(paginationParams),
      status,
    });
    const response = await httpClient.get<Batch<AdcmClusterOverviewStatusHost>>(
      `/api/v2/clusters/${clusterId}/statuses/hosts/?${query}`,
    );
    return response.data;
  }
}
