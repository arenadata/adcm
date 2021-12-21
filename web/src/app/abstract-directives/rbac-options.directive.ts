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
    const paramsWithOrdering$ = this._params$.asObservable().pipe(
      // the ordering is s required param for options requests
      filter((params) => params['ordering'])
    );

    const initial$ = paramsWithOrdering$.pipe(first());

    const debounced$ = paramsWithOrdering$.pipe(
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

  updateParam(key: string, value: any): void {
    let params = { ...this._params$.getValue() };
    if (value === null) {
      delete params[key];
    } else {
      params[key] = value;
    }
    this._params$.next(params);
  }
}
