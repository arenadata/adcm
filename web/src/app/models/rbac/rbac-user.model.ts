export interface RbacUserModel {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  email: string;
  is_superuser: boolean;
  password: string;
  url: string;
  profile: unknown;
  groups: unknown[];
}
