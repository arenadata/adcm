import { httpClient } from '@api/httpClient';
import { AdcmPrototypeVersions } from '@models/adcm';

export class AdcmPrototypesApi {
  public static async getPrototypeVersions() {
    const response = await httpClient.get<AdcmPrototypeVersions[]>('/api/v2/prototypes/versions');
    return response.data;
  }
}
