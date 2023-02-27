import { AuthCredentials } from './auth-credentials';

export interface LoginCredentials extends AuthCredentials {
  password: string;
}
