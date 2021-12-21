import { Component, forwardRef, OnInit, ViewChild } from '@angular/core';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import { ADD_SERVICE_PROVIDER } from '@app/shared/add-component/add-service-model';
import { RbacRoleService } from '@app/services/rbac-role.service';
import { RbacFormDirective } from '@app/shared/add-component/rbac-form.directive';
import { RbacRoleModel } from '@app/models/rbac/rbac-role.model';
import { RbacPermissionFormComponent } from '../permission-form/rbac-permission-form.component';

@Component({
  selector: 'app-rbac-role-form',
  templateUrl: './rbac-role-form.component.html',
  providers: [
    { provide: ADD_SERVICE_PROVIDER, useExisting: forwardRef(() => RbacRoleService) }
  ],
})
export class RbacRoleFormComponent extends RbacFormDirective<RbacRoleModel> implements OnInit {
  form: FormGroup = undefined;

  @ViewChild(RbacPermissionFormComponent) permissionForm: RbacPermissionFormComponent;

  ngOnInit(): void {
    this.form = new FormGroup({
      id: new FormControl(null),
      name: new FormControl({ value: '', disabled: this.value?.built_in }, [
        Validators.required,
        Validators.minLength(1),
        Validators.maxLength(160),
        Validators.pattern('^[a-zA-Z_]*$')
      ]),
      description: new FormControl({ value: '', disabled: this.value?.built_in }),
      display_name: new FormControl({ value: '', disabled: this.value?.built_in }),
      built_in: new FormControl(null),
      type: new FormControl('role'),
      category: new FormControl(['ADCM']),
      parametrized_by_type: new FormControl([]),
      child: new FormControl([], [
        Validators.required
      ]),
      url: new FormControl(null),
    });
    super.ngOnInit();
  }
}
