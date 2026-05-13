import type { RequestOptions } from '@api/httpClient/HttpClient';
import type {
  AdcmClusterGetProcessPayloadArgs,
  AdcmClusterGetStepPayloadArgs,
  AdcmClusterCreateProcessPayloadArgs,
  AdcmClusterPostOperationPayloadArgs,
  RunClusterDynamicActionPayload,
} from '@models/adcm/wizard';
import { AdcmWizardApi } from '../wizard';
import { httpClient } from '@api/httpClient';
import type { AdcmSubJob } from '@models/adcm';

export class AdcmClustersWizardApi {
  public static async getProcess({
    clusterId,
    actionId,
    processId,
    actionHostGroupId,
  }: AdcmClusterGetProcessPayloadArgs) {
    const endpoint = `/api/v2/clusters/${clusterId}/action-host-groups/${actionHostGroupId}/actions/${actionId}/processes/${processId}/`;

    return await AdcmWizardApi.getProcess(endpoint);
  }

  public static async getStep(
    { clusterId, actionId, processId, stepId, actionHostGroupId }: AdcmClusterGetStepPayloadArgs,
    options?: RequestOptions,
  ) {
    const endpoint = `/api/v2/clusters/${clusterId}/action-host-groups/${actionHostGroupId}/actions/${actionId}/processes/${processId}/steps/${stepId}/`;

    return await AdcmWizardApi.getStep(endpoint, options);
  }

  public static async createProcess({ clusterId, actionId, actionHostGroupId }: AdcmClusterCreateProcessPayloadArgs) {
    const endpoint = `/api/v2/clusters/${clusterId}/action-host-groups/${actionHostGroupId}/actions/${actionId}/processes/`;

    return await AdcmWizardApi.createProcess(endpoint);
  }

  public static async createOperation({
    clusterId,
    actionId,
    processId,
    operation,
    actionHostGroupId,
  }: AdcmClusterPostOperationPayloadArgs) {
    const endpoint = `/api/v2/clusters/${clusterId}/action-host-groups/${actionHostGroupId}/actions/${actionId}/processes/${processId}/operation/`;

    return await AdcmWizardApi.postOperation(endpoint, operation);
  }

  public static async runDynamicAction({
    clusterId,
    actionId,
    actionHostGroupId,
    actionRunConfig,
  }: RunClusterDynamicActionPayload) {
    await httpClient.post<AdcmSubJob>(
      `/api/v2/clusters/${clusterId}/action-host-groups/${actionHostGroupId}/actions/${actionId}/run/`,
      actionRunConfig,
    );
  }
}
