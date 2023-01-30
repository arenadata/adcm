import { Entity } from "@app/adwp";

export interface RbacAuditOperationsModel extends Entity {
  id: number;
  object_type: string;
  object_name: string;
  object_changes: AuditOperationsObjectChanges;
  operation_name: string;
  operation_type: string;
  operation_result: string;
  operation_time: string;
  username: string;
}

interface AuditOperationsObjectChanges {
  current: { [key: string]: any };
  previous: { [key: string]: any };
}

export interface AuditOperationsChangesHistory {
  attribute: string;
  old_value: any;
  new_value: any;
}
