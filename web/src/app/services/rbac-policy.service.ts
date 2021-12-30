import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from '@app/core/api';
import { environment } from '@env/environment';
import { FormModel } from '@app/shared/add-component/add-service-model';
import { EntityAbstractService } from '@app/abstract/entity.abstract.service';
import { RbacPolicyModel } from '@app/models/rbac/rbac-policy.model';
import { Params } from '@angular/router';
import { ListResult } from '@app/models/list-result';
import { map } from 'rxjs/operators';

@Injectable()
export class RbacPolicyService implements EntityAbstractService {
  constructor(protected api: ApiService) {}

  model(value?: any): FormModel {
    return {
      name: 'new policy',
      value: value
    };
  }

  delete(id: number): Observable<any> {
    return this.api.delete(`${environment.apiRoot}rbac/policy/${id}/`);
  }

  add(group: Partial<RbacPolicyModel>): Observable<RbacPolicyModel> {
    const params = { ...group };

    return this.api.post<RbacPolicyModel>(`${environment.apiRoot}rbac/policy/`, params);
  }

  update(url: string, params: Partial<RbacPolicyModel>): Observable<RbacPolicyModel> {
    return this.api.put<RbacPolicyModel>(url, params);
  }

  getList(param?: Params): Observable<RbacPolicyModel[]> {
    return this.api.get<ListResult<RbacPolicyModel>>(`${environment.apiRoot}rbac/policy/`, param)
      .pipe(map((list) => list.results));
  }

  getByUrl(url: string, params?: Params): Observable<RbacPolicyModel> {
    const p = { expand: 'object,role,user,group', ...params };

    return this.api.get(url, p);
  }

  get(id: number): Observable<RbacPolicyModel> {
    return this.api.get(`${environment.apiRoot}rbac/policy/${id}/`);
  }
}
