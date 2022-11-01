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

  getList(): Observable<RbacAuditOperationsModel[]> {
    return this.api.get<ListResult<RbacAuditOperationsModel>>(`${environment.apiRoot}audit/operation/`)
      .pipe(map((list) => list.results));
  }
}
