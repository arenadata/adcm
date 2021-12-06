import { Injectable } from '@angular/core';
import { FormModel, IAddService } from '../../../shared/add-component/add-service-model';
import { ICluster } from '../../../models/cluster';
import { Observable } from 'rxjs';
import { ApiService } from '../../../core/api';
import { environment } from '../../../../environments/environment';
import { RbacGroupModel } from '../../../models/rbac/rbac-group.model';
import { TypeName } from '../../../core/types';
import { Params } from '@angular/router';
import { map } from 'rxjs/operators';
import { ListResult } from '../../../models/list-result';
import { DeletableEntityAbstractService } from '../../../abstract/deletable-entity.abstract.service';


@Injectable()
export class RbacGroupService extends DeletableEntityAbstractService implements IAddService {
  constructor(
    protected api: ApiService,
  ) {
    super();
  }

  Cluster: ICluster;
  Current: any;

  model(name?: string): FormModel {
    return {
      name: 'group',
    };
  }

  add<T>(group: Partial<RbacGroupModel>): Observable<T> {
    const params = { ...group };
    return this.api.post<T>(`${environment.apiRoot}rbac/group/`, params);
  }

  getList<T = RbacGroupModel>(type: TypeName = 'rbac_group', param?: Params): Observable<T[]> {
    return this.api.get<ListResult<T>>(`${environment.apiRoot}rbac/group/`, param).pipe(map((list) => list.results));
  }

  delete(id: number): Observable<any> {
    throw new Error('Method not implemented.');
  }

}
