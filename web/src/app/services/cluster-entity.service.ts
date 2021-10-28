import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { EntityService } from '../abstract/entity-service';
import { environment } from '../../environments/environment';
import { ApiService } from '../core/api';
import { ICluster } from '../models/cluster';

@Injectable({
  providedIn: 'root',
})
export class ClusterEntityService extends EntityService<ICluster> {

  constructor(
    protected api: ApiService,
  ) {
    super(api);
  }

  get(
    id: number,
    params: { [key: string]: string } = {},
  ): Observable<ICluster> {
    return this.api.get(`${environment.apiRoot}cluster/${id}/`, params);
  }

}
