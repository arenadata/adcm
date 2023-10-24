interface UserRBACAuthSettings {
  blockTime: number;
  loginAttemptLimit: number;
  maxPasswordLength: number;
  minPasswordLength: number;
}

export interface UserRBAC {
  id: number;
  email: string;
  isSuperuser: boolean;
  lastName: string;
  username: string;
  failedLoginAttempts?: number;
  isActive?: boolean;
  profile?: string;
  // TODO: change to ENUM or Union
  type?: string;
  authSettings: UserRBACAuthSettings;
}
