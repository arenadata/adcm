import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiService } from '@app/core/api';
import { EntityService } from '@app/abstract/entity-service';
import { environment } from '@env/environment';
import { Service } from '@app/core/types';
import { HavingStatusTreeAbstractService } from '@app/abstract/having-status-tree.abstract.service';
import { ServiceStatusTree, StatusTree } from '@app/models/status-tree';

@Injectable({
  providedIn: 'root',
})
export class ServiceService extends EntityService<Service> implements HavingStatusTreeAbstractService<ServiceStatusTree, Service> {

  constructor(
    protected api: ApiService,
  ) {
    super(api);
  }

  get(
    id: number,
    params: { [key: string]: string } = {},
  ): Observable<Service> {
    return this.api.get(`${environment.apiRoot}service/${id}/`, params);
  }

  getStatusTree(id: number): Observable<ServiceStatusTree> {
    return this.api.get(`${environment.apiRoot}service/${id}/status/`);
  }

  entityStatusTreeToStatusTree(input: ServiceStatusTree, clusterId: number): StatusTree[] {
    return [{
      subject: {
        id: input.id,
        name: input.name,
        status: input.status,
      },
      children: input.hc.map(hc => ({
        subject: {
          id: hc.id,
          name: hc.name,
          status: hc.status,
        },
        children: hc.hosts.map(host => ({
          subject: {
            id: host.id,
            name: host.name,
            status: host.status,
            link: (id) => ['/cluster', clusterId.toString(), 'host', id.toString(), 'status'],
          },
          children: [],
        })),
      })),
    }];
  }

}
