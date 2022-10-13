import { Entity } from "@adwp-ui/widgets";

export interface RbacAuditOperationsModel extends Entity {
  id: number;
  object_type: string;
  object_name: string;
  operation_name: string;
  operation_type: string;
  operation_result: string;
  operation_time: string;
  username: string;
}
