import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { EntityService } from '../abstract/entity-service';
import { IHost } from '../models/host';
import { Host } from '../core/types';
import { environment } from '@env/environment';
import { ApiService } from '@app/core/api';
import { HostStatusTree, StatusTree } from '@app/models/status-tree';
import { HavingStatusTreeAbstractService } from '@app/abstract/having-status-tree.abstract.service';

@Injectable({
  providedIn: 'root',
})
export class HostService extends EntityService<IHost> implements HavingStatusTreeAbstractService<HostStatusTree> {

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

  getStatusTree(id: number): Observable<HostStatusTree> {
    return this.api.get(`${environment.apiRoot}host/${id}/status/`);
  }

  entityStatusTreeToStatusTree(input: HostStatusTree): StatusTree[] {
    return [{
      subject: {
        id: input.id,
        status: input.status,
        name: input.name,
      },
      children: input.hc.map((hc) => ({
        subject: {
          id: hc.id,
          status: hc.status,
          name: hc.name,
        },
        children: [],
      })),
    }];
  }

}
