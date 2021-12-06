import { Injectable } from '@angular/core';
import { FormModel, IAddService } from '../../../shared/add-component/add-service-model';
import { ICluster } from '../../../models/cluster';
import { Observable } from 'rxjs';
import { ApiService } from '../../../core/api';
import { environment } from '../../../../environments/environment';
import { RbacUserModel } from '../../../models/rbac/rbac-user.model';
import { Params } from '@angular/router';
import { ListResult } from '../../../models/list-result';
import { map } from 'rxjs/operators';

@Injectable()
export class RbacUserService implements IAddService {

  constructor(
    protected api: ApiService,
  ) {
  }

  Cluster: ICluster;
  Current: any;

  model(name?: string): FormModel {
    return {
      name: 'user',
    };
  }

  add<T>(group: Partial<RbacUserModel>): Observable<T> {
    const params = { ...group };

    return this.api.post<T>(`${environment.apiRoot}rbac/user/`, params);
  }

  update<T>(url: string, params: Partial<RbacUserModel>): Observable<T> {
    return this.api.put<T>(url, params);
  }


  getList<T = RbacUserModel>(type = 'rbac_user', param?: Params): Observable<T[]> {
    return this.api.get<ListResult<T>>(`${environment.apiRoot}rbac/user/`, param).pipe(map((list) => list.results));
  }
}
