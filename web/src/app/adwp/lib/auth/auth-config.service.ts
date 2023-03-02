import { InjectionToken } from '@angular/core';
import { AuthConfig } from './auth-config';

export const AuthConfigService = new InjectionToken<AuthConfig>('AuthConfig');
