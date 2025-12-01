import { httpClient } from '@api/httpClient';
import type {
  AdcmActionProcessStep,
  AdcmActionWizardProcess,
  AdcmWizardProcessOperation,
  AdcmWizardProcessOperationPayload,
} from '@models/adcm/wizard';
import type { RequestOptions } from '@api/httpClient/HttpClient';

export class AdcmWizardApi {
  public static async createProcess(endpoint: string) {
    const response = await httpClient.post<AdcmActionWizardProcess>(endpoint, {});

    return response.data;
  }

  public static async getProcess(endpoint: string) {
    const response = await httpClient.get<AdcmActionWizardProcess>(endpoint);

    return response.data;
  }

  public static async getStep(endpoint: string, options?: RequestOptions) {
    const response = await httpClient.get<AdcmActionProcessStep>(endpoint, options);

    return response.data;
  }

  public static async postOperation(link: string, operation: AdcmWizardProcessOperationPayload) {
    const response = await httpClient.post<AdcmWizardProcessOperation>(link, operation);

    return response.data;
  }
}
