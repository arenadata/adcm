import { Injectable } from '@angular/core';
import { FormModel, IAddService } from '../../../shared/add-component/add-service-model';
import { ICluster } from '../../../models/cluster';
import { Observable } from 'rxjs';
import { ApiService } from '../../../core/api';
import { environment } from '../../../../environments/environment';
import { RbacRoleModel } from '../../../models/rbac/rbac-role.model';

@Injectable()
export class RbacRoleService implements IAddService {

  constructor(protected api: ApiService) { }

  Cluster: ICluster;
  Current: any;

  model(name?: string): FormModel {
    return {
      name: 'role',
    };
  }

  add<T>(group: Partial<RbacRoleModel>): Observable<T> {
    const params = { ...group };
    return this.api.post<T>(`${environment.apiRoot}rbac/role/`, params);
  }
}
