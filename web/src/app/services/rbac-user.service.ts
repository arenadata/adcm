import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiService } from '@app/core/api';
import { environment } from '@env/environment';
import { RbacUserModel } from '@app/models/rbac/rbac-user.model';
import { Params } from '@angular/router';
import { ListResult } from '@app/models/list-result';
import { map } from 'rxjs/operators';
import { EntityAbstractService } from '@app/abstract/entity.abstract.service';
import { FormModel } from '@app/shared/add-component/add-service-model';

@Injectable()
export class RbacUserService implements EntityAbstractService {
  constructor(protected api: ApiService) {}

  model(value?: any): FormModel {
    return {
      name: 'User',
      value: value
    };
  }

  delete(id: number): Observable<any> {
    return this.api.delete(`${environment.apiRoot}rbac/user/${id}/`);
  }

  add(group: Partial<RbacUserModel>): Observable<RbacUserModel> {
    const params = { ...group };

    return this.api.post<RbacUserModel>(`${environment.apiRoot}rbac/user/`, params);
  }

  update(url: string, params: Partial<RbacUserModel>): Observable<RbacUserModel> {
    return this.api.patch<RbacUserModel>(url, params);
  }

  getByUrl(url: string, params?: Params): Observable<RbacUserModel> {
    const p = { expand: 'group', ...params };

    return this.api.get(url, p);
  }

  getList(param?: Params): Observable<RbacUserModel[]> {
    return this.api.get<ListResult<RbacUserModel>>(`${environment.apiRoot}rbac/user/`, param)
      .pipe(
        map((list) => list.results.filter(({ is_active }) => is_active)),
      );
  }

  resetLoginAttemps(id: number): Observable<any> {
    return this.api.post(`${environment.apiRoot}rbac/user/${id}/reset_failed_login_attempts/`, {});
  }

}
