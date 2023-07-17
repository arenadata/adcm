import { httpClient } from '@api/httpClient';
import { AdcmPrototypeVersionsFilter, AdcmPrototypeVersions } from '@models/adcm';
import qs from 'qs';

export class AdcmPrototypesApi {
  public static async getPrototypeVersions(filter: AdcmPrototypeVersionsFilter) {
    const query = qs.stringify(filter);
    const response = await httpClient.get<AdcmPrototypeVersions[]>(`/api/v2/prototypes/versions/?${query}`);
    return response.data;
  }

  public static async postAcceptLicense(prototypeId: number) {
    const response = await httpClient.post(`/api/v2/prototypes/${prototypeId}/license/accept/`);
    return response.data;
  }
}
