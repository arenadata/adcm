import { Directive, OnChanges, SimpleChange, SimpleChanges } from '@angular/core';
import { Params } from '@angular/router';
import { BehaviorSubject, merge, Observable } from 'rxjs';
import { RbacRoleModel } from '../models/rbac/rbac-role.model';
import { debounceTime, filter, first, skip, switchMap } from 'rxjs/operators';
import { EntityAbstractService } from '../abstract/entity.abstract.service';

const RBAC_ROLES_FILTERS_DEBOUNCE_TIME = 300;

@Directive()
export class RbacOptionsDirective implements OnChanges {
  private _params$: BehaviorSubject<Params>;

  options$: Observable<RbacRoleModel[]>;

  initialParams: Params = {};

  params: Params;

  constructor(service: EntityAbstractService) {
    this._params$ = new BehaviorSubject<Params>(this.initialParams);

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
        ...this.initialParams,
        ...this._params$.getValue(),
        ...params.currentValue
      });
    }
  }
}
