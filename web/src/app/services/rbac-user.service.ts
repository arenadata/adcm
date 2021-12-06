import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiService } from '@app/core/api';
import { environment } from '@env/environment';
import { DeletableEntityAbstractService } from '@app/abstract/deletable-entity.abstract.service';
import { RbacUserModel } from '@app/models/rbac/rbac-user.model';
import { Params } from '@angular/router';
import { ListResult } from '@app/models/list-result';
import { map } from 'rxjs/operators';
import { EntityAbstractService } from '@app/abstract/entity.abstract.service';

@Injectable()
export class RbacUserService implements EntityAbstractService, DeletableEntityAbstractService {

  constructor(
    protected api: ApiService,
  ) {}

  delete(id: number): Observable<unknown> {
    return this.api.delete(`${environment.apiRoot}rbac/user/${id}/`);
  }

  add<T>(group: Partial<RbacUserModel>): Observable<T> {
    const params = { ...group };

    return this.api.post<T>(`${environment.apiRoot}rbac/user/`, params);
  }

  update<T>(url: string, params: Partial<RbacUserModel>): Observable<T> {
    return this.api.put<T>(url, params);
  }

  getList<T = RbacUserModel>(param?: Params): Observable<T[]> {
    return this.api.get<ListResult<T>>(`${environment.apiRoot}rbac/user/`, param)
      .pipe(map((list) => list.results));
  }

}
