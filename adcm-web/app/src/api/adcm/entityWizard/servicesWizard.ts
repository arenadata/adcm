import type { RequestOptions } from '@api/httpClient/HttpClient';
import type {
  AdcmServiceGetProcessPayloadArgs,
  AdcmServiceGetStepPayloadArgs,
  AdcmServiceCreateProcessPayloadArgs,
  AdcmServicePostOperationPayloadArgs,
  RunServiceDynamicActionPayload,
} from '@models/adcm/wizard';
import { AdcmWizardApi } from '../wizard';
import { httpClient } from '@api/httpClient';
import type { AdcmSubJob } from '@models/adcm';

export class AdcmServicesWizardApi {
  public static async getProcess({
    clusterId,
    serviceId,
    actionId,
    processId,
    actionHostGroupId,
  }: AdcmServiceGetProcessPayloadArgs) {
    const endpoint = `/api/v2/clusters/${clusterId}/services/${serviceId}/action-host-groups/${actionHostGroupId}/actions/${actionId}/processes/${processId}/`;

    return await AdcmWizardApi.getProcess(endpoint);
  }

  public static async getStep(
    { clusterId, serviceId, actionId, processId, stepId, actionHostGroupId }: AdcmServiceGetStepPayloadArgs,
    options?: RequestOptions,
  ) {
    const endpoint = `/api/v2/clusters/${clusterId}/services/${serviceId}/action-host-groups/${actionHostGroupId}/actions/${actionId}/processes/${processId}/steps/${stepId}/`;

    return await AdcmWizardApi.getStep(endpoint, options);
  }

  public static async createProcess({
    clusterId,
    serviceId,
    actionHostGroupId,
    actionId,
  }: AdcmServiceCreateProcessPayloadArgs) {
    const endpoint = `/api/v2/clusters/${clusterId}/services/${serviceId}/action-host-groups/${actionHostGroupId}/actions/${actionId}/processes/`;

    return await AdcmWizardApi.createProcess(endpoint);
  }

  public static async createOperation({
    clusterId,
    serviceId,
    actionId,
    processId,
    operation,
    actionHostGroupId,
  }: AdcmServicePostOperationPayloadArgs) {
    const endpoint = `/api/v2/clusters/${clusterId}/services/${serviceId}/action-host-groups/${actionHostGroupId}/actions/${actionId}/processes/${processId}/operation/`;

    return await AdcmWizardApi.postOperation(endpoint, operation);
  }

  public static async runDynamicAction({
    clusterId,
    serviceId,
    actionId,
    actionRunConfig,
    actionHostGroupId,
  }: RunServiceDynamicActionPayload) {
    await httpClient.post<AdcmSubJob>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/action-host-groups/${actionHostGroupId}/actions/${actionId}/run/`,
      actionRunConfig,
    );
  }
}
