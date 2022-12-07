import { Injectable } from "@angular/core";
import { EntityAbstractService } from "../abstract/entity.abstract.service";
import { ApiService } from "../core/api";
import { FormModel } from "../shared/add-component/add-service-model";
import { Observable } from "rxjs";
import { ListResult } from "../models/list-result";
import { environment } from "../../environments/environment";
import { map } from "rxjs/operators";
import { RbacAuditLoginModel } from "../models/rbac/rbac-audit-login.model";

@Injectable()
export class RbacAuditLoginService implements EntityAbstractService {
  constructor(protected api: ApiService) {}

  model(value?: any): FormModel {
    return {
      name: 'Audit Login',
      value: value
    };
  }

  getList(): Observable<RbacAuditLoginModel[]> {
    return this.api.get<ListResult<RbacAuditLoginModel>>(`${environment.apiRoot}audit/login/`)
      .pipe(map((list) => list.results));
  }
}
