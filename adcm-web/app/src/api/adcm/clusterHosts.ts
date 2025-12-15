import { httpClient } from '@api/httpClient';
import type {
  AdcmMaintenanceMode,
  AdcmServiceComponent,
  Batch,
  AdcmClusterHost,
  AdcmClusterHostComponentsStates,
  AdcmClusterHostsFilter,
  AdcmSetMaintenanceModeResponse,
  AdcmHostComponentsFilter,
} from '@models/adcm';
import type {
  AdcmDynamicAction,
  AdcmDynamicActionDetails,
  AdcmDynamicActionRunConfig,
} from '@models/adcm/dynamicAction';
import type { PaginationParams, SortParams } from '@models/table';
import { prepareQueryParams } from '@utils/apiUtils';
import qs from 'qs';
import { AdcmWizardApi } from '@api/adcm/wizard';
import type { AdcmWizardProcessOperationPayload } from '@models/adcm/wizard';
import type { RequestOptions } from '@api/httpClient/HttpClient';

export class AdcmClusterHostsApi {
  public static async getClusterHosts(
    clusterId: number,
    filter: AdcmClusterHostsFilter,
    sortParams: SortParams,
    paginationParams: PaginationParams,
  ) {
    const queryParams = prepareQueryParams(filter, sortParams, paginationParams);

    const query = qs.stringify(queryParams);
    const response = await httpClient.get<Batch<AdcmClusterHost>>(`/api/v2/clusters/${clusterId}/hosts/?${query}`);
    return response.data;
  }

  public static async getHost(clusterId: number, hostId: number) {
    const response = await httpClient.get<AdcmClusterHost>(`/api/v2/clusters/${clusterId}/hosts/${hostId}/`);
    return response.data;
  }

  public static async toggleMaintenanceMode(clusterId: number, hostId: number, maintenanceMode: AdcmMaintenanceMode) {
    const response = await httpClient.post<AdcmSetMaintenanceModeResponse>(
      `/api/v2/clusters/${clusterId}/hosts/${hostId}/maintenance-mode/`,
      {
        maintenanceMode,
      },
    );

    return response.data;
  }

  public static async getClusterHostComponents(
    clusterId: number,
    hostId: number,
    sortParams: SortParams,
    paginationParams: PaginationParams,
    filter: AdcmHostComponentsFilter,
  ) {
    const queryParams = prepareQueryParams(filter, sortParams, paginationParams);

    const query = qs.stringify(queryParams);
    const response = await httpClient.get<Batch<AdcmServiceComponent>>(
      `/api/v2/clusters/${clusterId}/hosts/${hostId}/components/?${query}`,
    );

    return response.data;
  }

  public static async getClusterHostComponentsStates(clusterId: number, hostId: number) {
    const response = await httpClient.get<AdcmClusterHostComponentsStates>(
      `/api/v2/clusters/${clusterId}/hosts/${hostId}/statuses/`,
    );
    return response.data;
  }

  public static async getClusterHostOwnActions(clusterId: number, hostId: number) {
    const query = qs.stringify({ is_host_own_action: true });
    const response = await httpClient.get<AdcmDynamicAction[]>(
      `/api/v2/clusters/${clusterId}/hosts/${hostId}/actions/?${query}`,
    );
    return response.data;
  }

  public static async getClusterHostPrototypeActions(clusterId: number, hostId: number, prototypeId: number) {
    const query = qs.stringify({ is_host_own_action: false, prototype_id: prototypeId });
    const response = await httpClient.get<AdcmDynamicAction[]>(
      `/api/v2/clusters/${clusterId}/hosts/${hostId}/actions/?${query}`,
    );
    return response.data;
  }

  public static async getClusterHostComponentActions(clusterId: number, hostId: number, componentPrototypeId: number) {
    const query = qs.stringify({ is_host_own_action: false, prototype_id: componentPrototypeId });
    const response = await httpClient.get<AdcmDynamicAction[]>(
      `/api/v2/clusters/${clusterId}/hosts/${hostId}/actions/?${query}`,
    );
    return response.data;
  }

  public static async getClusterHostActionsDetails(clusterId: number, hostId: number, actionId: number) {
    const response = await httpClient.get<AdcmDynamicActionDetails>(
      `/api/v2/clusters/${clusterId}/hosts/${hostId}/actions/${actionId}/`,
    );
    return response.data;
  }

  public static async runClusterHostAction(
    clusterId: number,
    hostId: number,
    actionId: number,
    actionRunConfig: AdcmDynamicActionRunConfig,
  ) {
    const response = await httpClient.post(
      `/api/v2/clusters/${clusterId}/hosts/${hostId}/actions/${actionId}/run/`,
      actionRunConfig,
    );

    return response.data;
  }

  // action wizard
  public static async createHostActionWizardProcess(clusterId: number, hostId: number, actionId: number) {
    const endpoint = `/api/v2clusters/${clusterId}/hosts/${hostId}/actions/${actionId}/processes/`;

    return await AdcmWizardApi.createProcess(endpoint);
  }

  public static async getHostActionWizardProcess(
    clusterId: number,
    hostId: number,
    actionId: number,
    processId: number,
  ) {
    const endpoint = `/api/v2clusters/${clusterId}/hosts/${hostId}/actions/${actionId}/processes/${processId}/`;

    return await AdcmWizardApi.getProcess(endpoint);
  }

  public static async getHostActionWizardStep(
    clusterId: number,
    hostId: number,
    actionId: number,
    processId: number,
    stepId: number,
    options?: RequestOptions,
  ) {
    const endpoint = `/api/v2clusters/${clusterId}/hosts/${hostId}/actions/${actionId}/processes/${processId}/steps/${stepId}/`;

    return await AdcmWizardApi.getStep(endpoint, options);
  }

  public static async createHostActionWizardOperation(
    clusterId: number,
    hostId: number,
    actionId: number,
    processId: number,
    operation: AdcmWizardProcessOperationPayload,
  ) {
    const endpoint = `/api/v2clusters/${clusterId}/hosts/${hostId}/actions/${actionId}/processes/${processId}/operation/`;

    return await AdcmWizardApi.postOperation(endpoint, operation);
  }
}
