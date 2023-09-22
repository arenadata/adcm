export interface RbacUserFormData {
  username: string;
  firstName: string;
  lastName: string;
  email: string;
  groups: number[];
  password: string;
  confirmPassword: string;
  isSuperUser: boolean;
}
