import { InjectionToken } from '@angular/core';
import { SocketConfig } from '../socket/socket-config';

export const SocketConfigService = new InjectionToken<SocketConfig>('SocketConfig');
