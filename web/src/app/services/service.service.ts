import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiService } from '@app/core/api';
import { IClusterService } from '@app/models/cluster-service';
import { EntityService } from '@app/abstract/entity-service';

@Injectable({
  providedIn: 'root',
})
export class ServiceService extends EntityService<IClusterService> {

  constructor(
    protected api: ApiService,
  ) {
    super(api);
  }

  get(
    id: number,
    params: { [key: string]: string } = {},
  ): Observable<IClusterService> {
    return this.api.get(`api/v1/service/${id}/`, params);
  }

}
