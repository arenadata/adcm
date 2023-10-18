interface RbacUserFormDataAuthSettings {
  blockTime: number;
  loginAttemptLimit: number;
  maxPasswordLength: number;
  minPasswordLength: number;
}

export interface RbacUserFormData {
  username: string;
  firstName: string;
  lastName: string;
  email: string;
  groups: number[];
  password: string;
  confirmPassword: string;
  isSuperUser: boolean;
  authSettings?: RbacUserFormDataAuthSettings;
}
