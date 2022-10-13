import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from '@app/core/api';
import { environment } from '@env/environment';
import { FormModel } from '@app/shared/add-component/add-service-model';
import { EntityAbstractService } from '@app/abstract/entity.abstract.service';
import { Params } from '@angular/router';
import { ListResult } from '@app/models/list-result';
import { map } from 'rxjs/operators';
import { RbacAuditOperationsModel } from "../models/rbac/rbac-audit-operations.model";

@Injectable()
export class RbacAuditOperationsService implements EntityAbstractService {
  constructor(protected api: ApiService) {}

  model(value?: any): FormModel {
    return {
      name: 'Audit Operations',
      value: value
    };
  }

  delete(id: number): Observable<any> {
    return this.api.delete(`${environment.apiRoot}rbac/audit_operations/${id}/`);
  }

  add(group: Partial<RbacAuditOperationsModel>): Observable<RbacAuditOperationsModel> {
    const params = { ...group };

    return this.api.post<RbacAuditOperationsModel>(`${environment.apiRoot}rbac/audit_operations/`, params);
  }

  update(url: string, params: Partial<RbacAuditOperationsModel>): Observable<RbacAuditOperationsModel> {
    return this.api.put<RbacAuditOperationsModel>(url, params);
  }

  getList(param?: Params): Observable<RbacAuditOperationsModel[]> {
    const p = { 'built_in': 'false', ...param || {} };

    return this.api.get<ListResult<RbacAuditOperationsModel>>(`${environment.apiRoot}rbac/audit_operations/`, p)
      .pipe(map((list) => list.results));
  }

  getByUrl(url: string, params?: Params): Observable<RbacAuditOperationsModel> {
    const p = { expand: 'object,role,user,group', ...params };

    return this.api.get(url, p);
  }

  get(id: number): Observable<RbacAuditOperationsModel> {
    return this.api.get(`${environment.apiRoot}rbac/audit_operations/${id}/`);
  }
}
