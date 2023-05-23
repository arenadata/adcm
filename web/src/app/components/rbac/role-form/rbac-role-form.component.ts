import { Component, forwardRef, OnInit, ViewChild } from '@angular/core';
import { AbstractControl, FormControl, FormGroup, Validators } from '@angular/forms';
import { ADD_SERVICE_PROVIDER } from '@app/shared/add-component/add-service-model';
import { RbacRoleService } from '@app/services/rbac-role.service';
import { RbacFormDirective } from '@app/shared/add-component/rbac-form.directive';
import { RbacRoleModel } from '@app/models/rbac/rbac-role.model';
import { RbacPermissionFormComponent } from '../permission-form/rbac-permission-form.component';
import { AdwpStringHandler } from '@app/adwp';
import { MatChipInputEvent } from '@angular/material/chips';
import { CustomValidators } from '../../../shared/validators/custom-validators';

@Component({
  selector: 'app-rbac-role-form',
  templateUrl: './rbac-role-form.component.html',
  styleUrls: ['rbac-role-form.component.scss'],
  providers: [
    { provide: ADD_SERVICE_PROVIDER, useExisting: forwardRef(() => RbacRoleService) }
  ],
})
export class RbacRoleFormComponent extends RbacFormDirective<RbacRoleModel> implements OnInit {
  form: FormGroup = undefined;

  @ViewChild(RbacPermissionFormComponent) permissionForm: RbacPermissionFormComponent;

  nameHandler: AdwpStringHandler<RbacRoleModel> = (item: RbacRoleModel) => item.display_name;

  get categoryControl(): AbstractControl | null {
    return this.form.get('category');
  }

  rbacBeforeSave(form: FormGroup): RbacRoleModel {
    let categories = form.value?.category;
    const permissions = form.value.child;

    if (!form.value?.category?.length) {
      categories = permissions.reduce((acc, cur) => [...acc, ...cur.category], []);
    }

    return {
      ...form.value,
      category: categories
    };
  }

  ngOnInit(): void {
    this.form = new FormGroup({
      id: new FormControl(null),
      name: new FormControl({ value: '', disabled: this.value?.built_in }),
      description: new FormControl({ value: '', disabled: this.value?.built_in }),
      display_name: new FormControl({ value: '', disabled: this.value?.built_in }, [
        CustomValidators.required,
        Validators.minLength(2),
        Validators.maxLength(160),
        Validators.pattern('[a-zA-Z0-9_]+.*$')
      ]),
      any_category: new FormControl(null),
      built_in: new FormControl(null),
      type: new FormControl('role'),
      category: new FormControl({ value: [], disabled: this.value?.built_in }),
      parametrized_by_type: new FormControl([]),
      child: new FormControl([], [
        Validators.required
      ]),
      url: new FormControl(null),
    });
    super.ngOnInit();

    this.form.markAllAsTouched();
  }

  addKeywordFromInput(event: MatChipInputEvent): void {
    const value = (event.value || '').trim();
    if (value) {
      this.categoryControl.setValue([
        ...new Set([...this.categoryControl.value, value])
      ]);
    }
    event.input.value = '';
    this.categoryControl.markAsDirty();
  }

  removeKeyword(category: string): void {
    const categories = [...this.categoryControl?.value || []];
    const index = categories.indexOf(category);

    if (index >= 0) {
      categories.splice(index, 1);
    }

    this.categoryControl.setValue(categories);
    this.categoryControl.markAsDirty();
  }
}
