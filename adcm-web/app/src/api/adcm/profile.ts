import { httpClient } from '@api/httpClient';
import { AdcmProfileChangePassword, AdcmProfileUser } from '@models/adcm/profile';

export class AdcmProfileApi {
  public static async getProfile() {
    const response = await httpClient.get<AdcmProfileUser>('/api/v2/profile/');
    return response.data;
  }

  public static async changePassword(payload: AdcmProfileChangePassword) {
    await httpClient.patch('/api/v2/profile/', payload);
  }
}
