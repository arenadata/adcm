interface AdcmProfileUserAuthSettings {
  blockTime: number;
  loginAttemptLimit: number;
  maxPasswordLength: number;
  minPasswordLength: number;
}

export interface AdcmProfileUser {
  id: number;
  username: string;
  email: string;
  firstName: string;
  lastName: string;
  isSuperUser: boolean;
  authSettings: AdcmProfileUserAuthSettings;
}

export interface AdcmProfileChangePassword {
  currentPassword: string;
  newPassword: string;
}
