import { Component, forwardRef, OnInit } from '@angular/core';
import { ADD_SERVICE_PROVIDER } from "@app/shared/add-component/add-service-model";
import { RbacAuditOperationsService } from "@app/services/rbac-audit-operations.service";
import { FormControl, FormGroup } from "@angular/forms";
import { RbacUserModel } from "@app/models/rbac/rbac-user.model";
import { RbacAuditOperationsModel } from "@app/models/rbac/rbac-audit-operations.model";
import { IColumns } from "@adwp-ui/widgets";

@Component({
  selector: 'app-rbac-audit-operations-form',
  templateUrl: './rbac-audit-operations-form.component.html',
  styleUrls: ['./rbac-audit-operations-form.component.scss'],
  providers: [
    { provide: ADD_SERVICE_PROVIDER, useExisting: forwardRef(() => RbacAuditOperationsService) }
  ]
})
export class RbacAuditOperationsFormComponent implements OnInit {

  listColumns = [
    {
      label: 'Attribute',
      headerClassName: 'width100',
      className: 'width100',
      value: (row) => row.object_changes,
    },
    {
      label: 'Old value',
      value: (row) => row.object_name,
    },
    {
      label: 'New Value',
      value: (row) => row.operation_name,
    }
  ] as IColumns<RbacAuditOperationsModel>;

  get auditOperationsForm(): FormGroup {
    return this.form.get('audit_operations') as FormGroup;
  }

  form = new FormGroup({
    audit_operations: new FormGroup({
      id: new FormControl(null),
      attribute: new FormControl(null),
      old_value: new FormControl(null),
      new_value: new FormControl(null),
    })
  })

  constructor() { }

  ngOnInit(): void {
    this._setValue(null);
    this.form.markAllAsTouched();
  }

  rbacBeforeSave(value: any): Partial<RbacUserModel> {
    return value.audit_operations;
  }

  /**
   * Need to set form value and form value to confirm password
   *
   * @param value
   * @private
   */
  private _setValue(value: RbacAuditOperationsModel): void {
    if (value) {
      // const type: string = this.value?.type;
      // ToDo(lihih) the "adwp-list" should not change the composition of the original model.
      //  Now he adds the "checked" key to the model
      // this._updateAndSetValueForForm(this.userForm);
      // this.confirmForm.setValue({ password: this.value.password });
      // this.form.get('user.username').disable();
      //
      // if (type === 'ldap' || value?.is_active === false) {
      //   this.userForm.controls.first_name.disable();
      //   this.userForm.controls.last_name.disable();
      //   this.userForm.controls.email.disable();
      //   this.userForm.controls.password.disable();
      //   this.confirmForm.controls.password.disable();
      // }
      //
      // if (value?.is_active === false) {
      //   this.userForm.controls.group.disable();
      //   this.userForm.controls.is_superuser.disable();
      // }
    }
  }

}
