import type {
  AdcmService,
  Batch,
  AdcmServicesFilter,
  AdcmServicePrototype,
  AdcmMaintenanceMode,
  AdcmSetMaintenanceModeResponse,
} from '@models/adcm';
import { httpClient } from '@api/httpClient';
import qs from 'qs';
import { prepareQueryParams } from '@utils/apiUtils';
import type { PaginationParams, SortParams } from '@models/table';
import type {
  AdcmDynamicAction,
  AdcmDynamicActionDetails,
  AdcmDynamicActionRunConfig,
} from '@models/adcm/dynamicAction';
import type { AdcmWizardProcessOperationPayload } from '@models/adcm/wizard';
import { AdcmWizardApi } from '@api';
import type { RequestOptions } from '@api/httpClient/HttpClient';

export class AdcmClusterServicesApi {
  public static async getClusterServices(
    clusterId: number,
    filter?: AdcmServicesFilter,
    sortParams?: SortParams,
    paginationParams?: PaginationParams,
  ) {
    const queryParams = prepareQueryParams(filter, sortParams, paginationParams);

    const query = qs.stringify(queryParams);
    const response = await httpClient.get<Batch<AdcmService>>(`/api/v2/clusters/${clusterId}/services/?${query}`);
    return response.data;
  }

  public static async getClusterServicePrototypes(clusterId: number) {
    const response = await httpClient.get<AdcmServicePrototype[]>(`/api/v2/clusters/${clusterId}/service-prototypes/`);
    return response.data;
  }

  // return AdcmServicePrototype[] for not added service to cluster
  public static async getClusterServiceCandidates(clusterId: number) {
    const response = await httpClient.get<AdcmServicePrototype[]>(`/api/v2/clusters/${clusterId}/service-candidates/`);
    return response.data;
  }

  public static async addClusterService(clusterId: number, serviceIds: number[]) {
    const prototypeIds = serviceIds.map((id) => ({ prototypeId: id }));
    await httpClient.post(`/api/v2/clusters/${clusterId}/services/`, prototypeIds);
  }

  public static async deleteClusterService(clusterId: number, servicesId: number) {
    await httpClient.delete(`/api/v2/clusters/${clusterId}/services/${servicesId}`);
  }

  public static async getClusterServiceActions(clusterId: number, serviceId: number) {
    const response = await httpClient.get<AdcmDynamicAction[]>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/actions/`,
    );
    return response.data;
  }

  public static async getClusterServiceActionDetails(clusterId: number, serviceId: number, actionId: number) {
    const response = await httpClient.get<AdcmDynamicActionDetails>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/actions/${actionId}/`,
    );
    return response.data;
  }

  public static async toggleMaintenanceMode(
    clusterId: number,
    serviceId: number,
    maintenanceMode: AdcmMaintenanceMode,
  ) {
    const response = await httpClient.post<AdcmSetMaintenanceModeResponse>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/maintenance-mode/`,
      {
        maintenanceMode,
      },
    );

    return response.data;
  }

  public static async runClusterServiceAction(
    clusterId: number,
    serviceId: number,
    actionId: number,
    actionRunConfig: AdcmDynamicActionRunConfig,
  ) {
    const response = await httpClient.post(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/actions/${actionId}/run/`,
      actionRunConfig,
    );

    return response.data;
  }

  // action wizard
  public static async createServiceActionWizardProcess(clusterId: number, serviceId: number, actionId: number) {
    const endpoint = `/api/v2/clusters/${clusterId}/services/${serviceId}/actions/${actionId}/processes/`;

    return await AdcmWizardApi.createProcess(endpoint);
  }

  public static async getServiceActionWizardProcess(
    clusterId: number,
    serviceId: number,
    actionId: number,
    processId: number,
  ) {
    const endpoint = `/api/v2/clusters/${clusterId}/services/${serviceId}/actions/${actionId}/processes/${processId}/`;

    return await AdcmWizardApi.getProcess(endpoint);
  }

  public static async getServiceActionWizardStep(
    clusterId: number,
    serviceId: number,
    actionId: number,
    processId: number,
    stepId: number,
    options?: RequestOptions,
  ) {
    const endpoint = `/api/v2/clusters/${clusterId}/services/${serviceId}/actions/${actionId}/processes/${processId}/steps/${stepId}/`;

    return await AdcmWizardApi.getStep(endpoint, options);
  }

  public static async createServiceActionWizardOperation(
    clusterId: number,
    serviceId: number,
    actionId: number,
    processId: number,
    operation: AdcmWizardProcessOperationPayload,
  ) {
    const endpoint = `/api/v2/clusters/${clusterId}/services/${serviceId}/actions/${actionId}/processes/${processId}/operation/`;

    return await AdcmWizardApi.postOperation(endpoint, operation);
  }
}
