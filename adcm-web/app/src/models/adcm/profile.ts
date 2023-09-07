export interface AdcmProfileUser {
  id: number;
  username: string;
  email: string;
  firstName: string;
  lastName: string;
  isSuperuser: boolean;
}

export interface AdcmProfileChangePassword {
  currentPassword: string;
  newPassword: string;
}
