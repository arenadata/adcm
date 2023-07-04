export interface UserRBAC {
  id: number;
  email: string;
  failedLoginAttempts: number;
  isActive: boolean;
  isSuperuser: boolean;
  lastName: string;
  profile: string;
  // TODO: change to ENUM or Union
  type: string;
  username: string;
}
