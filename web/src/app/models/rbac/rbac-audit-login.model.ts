import { Entity } from "@adwp-ui/widgets";

export interface RbacAuditLoginModel extends Entity {
  id: number
  login_details: LoginDetails;
  login_result: string;
  login_time: string;
  url: string;
  user_id: number;
}

interface LoginDetails {
  username: string;
}
