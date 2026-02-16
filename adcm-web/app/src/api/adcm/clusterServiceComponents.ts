import { httpClient } from '@api/httpClient';
import type { AdcmMaintenanceMode, AdcmServiceComponent, AdcmSetMaintenanceModeResponse, Batch } from '@models/adcm';
import type {
  AdcmDynamicAction,
  AdcmDynamicActionDetails,
  AdcmDynamicActionRunConfig,
} from '@models/adcm/dynamicAction';
import type { SortParams, PaginationParams } from '@models/table';
import { prepareQueryParams } from '@utils/apiUtils';
import qs from 'qs';
import { AdcmWizardApi } from '@api/adcm/wizard';
import type { RequestOptions } from '@api/httpClient/HttpClient';
import type { AdcmWizardProcessOperationPayload } from '@models/adcm/wizard';

export class AdcmClusterServiceComponentsApi {
  public static async getServiceComponents(
    clusterId: number,
    serviceId: number,
    sortParams: SortParams,
    paginationParams: PaginationParams,
  ) {
    const queryParams = prepareQueryParams(undefined, sortParams, paginationParams);

    const query = qs.stringify(queryParams);
    const response = await httpClient.get<Batch<AdcmServiceComponent>>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/components/?${query}`,
    );

    return response.data;
  }

  public static async getServiceComponent(clusterId: number, serviceId: number, componentId: number) {
    const response = await httpClient.get<AdcmServiceComponent>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/components/${componentId}/`,
    );

    return response.data;
  }

  public static async toggleMaintenanceMode(
    clusterId: number,
    serviceId: number,
    componentId: number,
    maintenanceMode: AdcmMaintenanceMode,
  ) {
    const response = await httpClient.post<AdcmSetMaintenanceModeResponse>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/components/${componentId}/maintenance-mode/`,
      { maintenanceMode },
    );

    return response.data;
  }

  public static async getClusterServiceComponentsActions(clusterId: number, serviceId: number, componentId: number) {
    const response = await httpClient.get<AdcmDynamicAction[]>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/components/${componentId}/actions/`,
    );
    return response.data;
  }

  public static async getClusterServiceComponentActionDetails(
    clusterId: number,
    serviceId: number,
    componentId: number,
    actionId: number,
  ) {
    const response = await httpClient.get<AdcmDynamicActionDetails>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/components/${componentId}/actions/${actionId}/`,
    );
    return response.data;
  }

  public static async runClusterServiceComponentAction(
    clusterId: number,
    serviceId: number,
    componentId: number,
    actionId: number,
    actionRunConfig: AdcmDynamicActionRunConfig,
  ) {
    const response = await httpClient.post(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/components/${componentId}/actions/${actionId}/run/`,
      actionRunConfig,
    );

    return response.data;
  }

  // action wizard
  public static async createClusterServiceComponentActionWizardProcess(
    clusterId: number,
    serviceId: number,
    componentId: number,
    actionId: number,
  ) {
    const endpoint = `/api/v2/clusters/${clusterId}/services/${serviceId}/components/${componentId}/actions/${actionId}/processes/`;

    return await AdcmWizardApi.createProcess(endpoint);
  }

  public static async getClusterServiceComponentActionWizardProcess(
    clusterId: number,
    serviceId: number,
    componentId: number,
    actionId: number,
    processId: number,
  ) {
    const endpoint = `/api/v2/clusters/${clusterId}/services/${serviceId}/components/${componentId}/actions/${actionId}/processes/${processId}/`;

    return await AdcmWizardApi.getProcess(endpoint);
  }

  public static async getClusterServiceComponentActionWizardStep(
    clusterId: number,
    serviceId: number,
    componentId: number,
    actionId: number,
    processId: number,
    stepId: number,
    options?: RequestOptions,
  ) {
    const endpoint = `/api/v2/clusters/${clusterId}/services/${serviceId}/components/${componentId}/actions/${actionId}/processes/${processId}/steps/${stepId}/`;

    return await AdcmWizardApi.getStep(endpoint, options);
  }

  public static async createClusterServiceComponentActionWizardOperation(
    clusterId: number,
    serviceId: number,
    componentId: number,
    actionId: number,
    processId: number,
    operation: AdcmWizardProcessOperationPayload,
  ) {
    const endpoint = `/api/v2/clusters/${clusterId}/services/${serviceId}/components/${componentId}/actions/${actionId}/processes/${processId}/operation/`;

    return await AdcmWizardApi.postOperation(endpoint, operation);
  }
}
