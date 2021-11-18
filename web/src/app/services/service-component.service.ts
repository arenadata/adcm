import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiService } from '@app/core/api';
import { IServiceComponent } from '@app/models/service-component';
import { EntityService } from '@app/abstract/entity-service';
import { environment } from '@env/environment';
import { HavingStatusTreeAbstractService } from '@app/abstract/having-status-tree.abstract.service';
import { HostComponentStatusTree, StatusTree } from '@app/models/status-tree';

@Injectable({
  providedIn: 'root',
})
export class ServiceComponentService extends EntityService<IServiceComponent> implements HavingStatusTreeAbstractService<HostComponentStatusTree, IServiceComponent> {

  constructor(
    protected api: ApiService,
  ) {
    super(api);
  }

  get(
    id: number,
    params: { [key: string]: string } = {},
  ): Observable<IServiceComponent> {
    return this.api.get(`${environment.apiRoot}component/${id}`, params);
  }

  getStatusTree(id: number): Observable<HostComponentStatusTree> {
    return this.api.get(`${environment.apiRoot}component/${id}/status/`);
  }

  entityStatusTreeToStatusTree(input: HostComponentStatusTree, clusterId: number): StatusTree[] {
    return [{
      subject: {
        id: input.id,
        name: input.name,
        status: input.status,
      },
      children: input.hosts.map(host => ({
        subject: {
          id: host.id,
          name: host.name,
          status: host.status,
          link: (id) => ['/cluster', clusterId.toString(), 'host', id.toString(), 'status'],
        },
        children: [],
      })),
    }];
  }

}
