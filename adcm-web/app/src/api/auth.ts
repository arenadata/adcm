import { httpClient } from './httpClient';

export class AuthApi {
  public static async login(username: string, password: string) {
    const response = await httpClient.post<{ token: string }>('/api/v2/login/', {
      username,
      password,
    });

    return response.data;
  }

  public static async logout() {
    const response = await httpClient.post('/api/v2/logout/');
    return response.data;
  }
}
