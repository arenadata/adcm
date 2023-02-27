export enum DjangoErrorCode {
  AuthError = 'AUTH_ERROR',
}

export enum DjangoErrorLevel {
  Error = 'error',
}

export interface DjangoHttpError {
  code: DjangoErrorCode;
  desc: string;
  level: DjangoErrorLevel;
}
