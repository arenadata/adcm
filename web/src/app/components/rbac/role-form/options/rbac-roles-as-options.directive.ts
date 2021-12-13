import { Directive, Inject, Input, OnChanges, SimpleChange, SimpleChanges } from '@angular/core';
import { BehaviorSubject, merge, Observable } from 'rxjs';
import { AdwpStringHandler } from '@adwp-ui/widgets';
import { RbacRoleModel } from '../../../../models/rbac/rbac-role.model';
import { RbacRoleService } from '../../../../services/rbac-role.service';
import { AdwpHandler } from '../../../../../../../../adwp_ui/projects/widgets/src/lib/cdk';
import { Params } from '@angular/router';
import { debounceTime, filter, first, skip, switchMap } from 'rxjs/operators';

const RBAC_ROLES_INITIAL_PARAMS: Params = {
  type: 'business'
};

const RBAC_ROLES_FILTERS_DEBOUNCE_TIME = 300;

@Directive({
  selector: '[appRbacRolesAsOptions], [rbac-roles-as-options]',
  exportAs: 'rbacRoles'
})
export class RbacRolesAsOptionsDirective implements OnChanges {
  @Input('rbac-roles-as-options')
  params: Params;

  private _params$: BehaviorSubject<Params>;

  options$: Observable<RbacRoleModel[]>;

  id: AdwpStringHandler<RbacRoleModel> = (item: RbacRoleModel) => String(item.id);

  label: AdwpStringHandler<RbacRoleModel> = (item: RbacRoleModel) => item.name;

  category: AdwpHandler<RbacRoleModel, string[]> = (item: RbacRoleModel) => item.category;

  constructor(@Inject(RbacRoleService) public service: RbacRoleService) {
    this._params$ = new BehaviorSubject<Params>(RBAC_ROLES_INITIAL_PARAMS);

    const initial$ = this._params$.pipe(
      first()
    );

    const debounced$ = this._params$.pipe(
      skip(1),
      debounceTime(RBAC_ROLES_FILTERS_DEBOUNCE_TIME)
    );

    this.options$ = merge(initial$, debounced$).pipe(
      switchMap((params) => service.getList(params)),
      filter((v) => !!v)
    );
  }

  ngOnChanges(changes: SimpleChanges): void {
    this.handleParamsChanges(changes['params']);
  }

  private handleParamsChanges(params: SimpleChange): void {
    if (params && params.currentValue) {
      this._params$.next({
        ...RBAC_ROLES_INITIAL_PARAMS,
        ...this._params$.getValue(),
        ...params.currentValue
      });
    }
  }
}
