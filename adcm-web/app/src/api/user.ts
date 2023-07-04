import { httpClient } from './httpClient';
import { UserRBAC } from '@models/RBAC';

export class UserApi {
  public static async login(username: string, password: string) {
    /**
     * Humor time: we don't use this token, we send request to this url, because:
     * 1) it return response with two cookies: 'sessionid' and 'crftoken', which need for another request to API
     * 2) original django endpoint POST: '/auth/login' can send two cookie too, but also return HTML page with login form (!)
     *    if user/pass will not correct - POST: '/auth/login' return 200 OK. And form will have paragraph with error message
     */
    const response = await httpClient.post<{ token: string }>('/api/v1/rbac/token/', {
      username,
      password,
    });

    return response.data;
  }

  public static async logout() {
    /**
     * django crushes (500 internal server error) when /auth/logout/ without 'next' get-param
     */
    const response = await httpClient.get('/auth/logout/?next=/api/v1/adcm/');
    return response.data;
  }

  public static async getCurrentUser() {
    const response = await httpClient.get<UserRBAC>('/api/v1/rbac/me/');
    return response.data;
  }
}
