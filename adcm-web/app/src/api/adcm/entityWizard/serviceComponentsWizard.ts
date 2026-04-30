import type {
  AdcmComponentCreateProcessPayloadArgs,
  AdcmComponentGetProcessPayloadArgs,
  AdcmComponentGetStepPayloadArgs,
  AdcmComponentPostOperationPayloadArgs,
  RunComponentDynamicActionPayload,
} from '@models/adcm/wizard';
import type { RequestOptions } from '@api/httpClient/HttpClient';
import { AdcmWizardApi } from '../wizard';
import { httpClient } from '@api/httpClient';
import type { AdcmSubJob } from '@models/adcm';

export class AdcmServiceComponentsWizardApi {
  public static async getProcess({
    clusterId,
    serviceId,
    componentId,
    actionId,
    processId,
    actionHostGroupId,
  }: AdcmComponentGetProcessPayloadArgs) {
    const endpoint = `/api/v2/clusters/${clusterId}/services/${serviceId}/components/${componentId}/action-host-groups/${actionHostGroupId}/actions/${actionId}/processes/${processId}/`;

    return await AdcmWizardApi.getProcess(endpoint);
  }

  public static async getStep(
    { clusterId, serviceId, componentId, actionId, processId, stepId }: AdcmComponentGetStepPayloadArgs,
    options?: RequestOptions,
  ) {
    const endpoint = `/api/v2/clusters/${clusterId}/services/${serviceId}/components/${componentId}/actions/${actionId}/processes/${processId}/steps/${stepId}/`;

    return await AdcmWizardApi.getStep(endpoint, options);
  }

  public static async createProcess({
    clusterId,
    serviceId,
    componentId,
    actionHostGroupId,
    actionId,
  }: AdcmComponentCreateProcessPayloadArgs) {
    const endpoint = `/api/v2/clusters/${clusterId}/services/${serviceId}/components/${componentId}/action-host-groups/${actionHostGroupId}/actions/${actionId}/processes/`;

    return await AdcmWizardApi.createProcess(endpoint);
  }

  public static async createOperation({
    clusterId,
    serviceId,
    componentId,
    actionId,
    processId,
    operation,
    actionHostGroupId,
  }: AdcmComponentPostOperationPayloadArgs) {
    const endpoint = `/api/v2/clusters/${clusterId}/services/${serviceId}/components/${componentId}/action-host-groups/${actionHostGroupId}/actions/${actionId}/processes/${processId}/operation/`;

    return await AdcmWizardApi.postOperation(endpoint, operation);
  }

  public static async runDynamicAction({
    clusterId,
    serviceId,
    componentId,
    actionId,
    actionRunConfig,
    actionHostGroupId,
  }: RunComponentDynamicActionPayload) {
    await httpClient.post<AdcmSubJob>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/components/${componentId}/action-host-groups/${actionHostGroupId}/actions/${actionId}/run/`,
      actionRunConfig,
    );
  }
}
