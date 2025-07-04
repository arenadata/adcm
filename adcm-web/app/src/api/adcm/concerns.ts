import { httpClient } from '@api/httpClient';

export class AdcmConcernsApi {
  public static async deleteConcern(concernId: number) {
    await httpClient.delete(`/api/v2/concerns/${concernId}`);
  }
}
