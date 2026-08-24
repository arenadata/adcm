import { httpClient } from '@api/httpClient';
import type {
  AdcmClusterOverviewStatusHost,
  AdcmClusterOverviewStatusService,
  AdcmHostStatus,
  AdcmMaintenanceMode,
  AdcmServiceStatus,
  Batch,
} from '@models/adcm';
import type { PaginationParams } from '@models/table';
import { prepareLimitOffset } from '@utils/apiUtils';
import qs from 'qs';

type ClusterStatusesQuery = {
  status?: AdcmServiceStatus | AdcmHostStatus;
  maintenanceMode?: AdcmMaintenanceMode;
  displayName?: string;
  name?: string;
};

export class AdcmClusterOverviewApi {
  public static async getClusterServicesStatuses(
    clusterId: number,
    paginationParams: PaginationParams,
    status?: AdcmServiceStatus,
    maintenanceMode?: AdcmMaintenanceMode,
    displayName?: string,
  ) {
    const query = qs.stringify({
      ...prepareLimitOffset(paginationParams),
      status,
      maintenanceMode,
      displayName: displayName || undefined,
    } satisfies ClusterStatusesQuery);

    const response = await httpClient.get<Batch<AdcmClusterOverviewStatusService>>(
      `/api/v2/clusters/${clusterId}/statuses/services/?${query}`,
    );

    return response.data;
  }

  public static async getClusterHostsStatuses(
    clusterId: number,
    paginationParams: PaginationParams,
    status?: AdcmHostStatus,
    maintenanceMode?: AdcmMaintenanceMode,
    name?: string,
  ) {
    const query = qs.stringify({
      ...prepareLimitOffset(paginationParams),
      status,
      maintenanceMode,
      name: name || undefined,
    } satisfies ClusterStatusesQuery);

    const response = await httpClient.get<Batch<AdcmClusterOverviewStatusHost>>(
      `/api/v2/clusters/${clusterId}/statuses/hosts/?${query}`,
    );
    return response.data;
  }
}
