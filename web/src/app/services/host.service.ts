import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { EntityService } from '../abstract/entity-service';
import { IHost } from '../models/host';
import { Host } from '../core/types';
import { environment } from '@env/environment';
import { ApiService } from '@app/core/api';

@Injectable({
  providedIn: 'root',
})
export class HostService extends EntityService<IHost> {

  constructor(
    protected api: ApiService,
  ) {
    super(api);
  }

  get(
    id: number,
    params: { [key: string]: string } = {},
  ): Observable<IHost> {
    return this.api.get(`${environment.apiRoot}host/${id}/`, params);
  }

  addToCluster(hostId: number, clusterId: number): Observable<Host> {
    return this.api.post<Host>(`${environment.apiRoot}cluster/${clusterId}/host/`, { host_id: hostId });
  }

}
