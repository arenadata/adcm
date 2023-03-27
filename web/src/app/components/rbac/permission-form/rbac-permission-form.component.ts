import { Component, Inject, Input } from '@angular/core';
import { RbacFormDirective } from '../../../shared/add-component/rbac-form.directive';
import { RbacRoleModel } from '../../../models/rbac/rbac-role.model';
import { FormGroup } from '@angular/forms';
import { ADWP_DEFAULT_STRINGIFY, adwpDefaultProp, AdwpHandler, AdwpMatcher, AdwpStringHandler } from '@app/adwp';
import { RbacRoleService } from '../../../services/rbac-role.service';
import { MatDialog } from '@angular/material/dialog';
import { Observable } from 'rxjs';
import { IAddService } from '../../../shared/add-component/add-service-model';
import { Params } from '@angular/router';

@Component({
  selector: 'app-rbac-permission-form',
  templateUrl: './rbac-permission-form.component.html',
  styleUrls: ['./rbac-permission-form.component.scss']
})
export class RbacPermissionFormComponent extends RbacFormDirective<RbacRoleModel> {
  @Input()
  form: FormGroup;

  @Input()
  @adwpDefaultProp()
  options: RbacRoleModel[] = [];

  @Input()
  idHandler: AdwpStringHandler<RbacRoleModel>;

  @Input()
  nameHandler: AdwpStringHandler<RbacRoleModel>;

  @Input()
  controlName: string;

  filter: Params = {
    type: 'business',
    limit: 100
  };

  categories$: Observable<string[]>;

  matcher: AdwpMatcher<RbacRoleModel> = (
    item: RbacRoleModel,
    search: RbacRoleModel[],
    stringify: AdwpHandler<RbacRoleModel, string> = ADWP_DEFAULT_STRINGIFY,
  ) => !search.map(stringify).includes(stringify(item));

  constructor(@Inject(RbacRoleService) service: RbacRoleService, dialog: MatDialog) {
    super(service as unknown as IAddService, dialog);

    this.categories$ = service.getCategories();
  }

  save(): void {
    this.form.controls[this.controlName].setValue(this.value);
    this.form.markAsDirty();
  }
}
