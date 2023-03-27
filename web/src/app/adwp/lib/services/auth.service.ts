import { Inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiService } from './api.service';
import { AuthConfig } from '../auth/auth-config';
import { AuthConfigService } from '../auth/auth-config.service';
import { AuthCredentials } from '../models/auth-credentials';


@Injectable({ providedIn: 'root' })
export class AuthService {

  readonly TOKEN_COOKIE_STORAGE_NAME = 'token-cookie-name';

  constructor(
    @Inject(AuthConfigService) public config: AuthConfig,
    protected api: ApiService,
  ) {}

  login(username: string, password: string): Observable<void> {
    return this.api.post(`login`, { username, password }, { root: this.config.uiApiRoot });
  }

  checkAuth(): Observable<AuthCredentials> {
    return this.api.get(`auth_status`, { root: this.config.uiApiRoot, ignoreErrors: [401] });
  }

  logout(): Observable<void> {
    return this.api.post(`logout`, {}, { root: this.config.uiApiRoot });
  }

  setTokenCookieName(cookieName: string): void {
    sessionStorage.setItem(this.TOKEN_COOKIE_STORAGE_NAME, cookieName);
  }

  getTokenCookieName(): string {
    return sessionStorage.getItem(this.TOKEN_COOKIE_STORAGE_NAME);
  }

}
