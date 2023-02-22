import { InjectionToken } from '@angular/core';
import { ApiConfig } from './api-config';

export const ApiConfigService = new InjectionToken<ApiConfig>('ApiConfig');
