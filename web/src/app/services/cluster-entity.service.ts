import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { EntityService } from '@app/abstract/entity-service';
import { environment } from '@env/environment';
import { ApiService } from '@app/core/api';
import { ICluster } from '@app/models/cluster';
import { ClusterStatusTree, StatusTree } from '@app/models/status-tree';
import { HavingStatusTreeAbstractService } from '@app/abstract/having-status-tree.abstract.service';

@Injectable({
  providedIn: 'root',
})
export class ClusterEntityService extends EntityService<ICluster> implements HavingStatusTreeAbstractService<ClusterStatusTree, ICluster> {

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

  getStatusTree(id: number): Observable<ClusterStatusTree> {
    return this.api.get(`${environment.apiRoot}cluster/${id}/status/`);
  }

  entityStatusTreeToStatusTree(input: ClusterStatusTree): StatusTree[] {
    const hostsStatus = input.chilren.hosts.every((host) => host.status === 0) ? 0 : 16;
    const servicesStatus = input.chilren.services.every((service) => service.status === 0) ? 0 : 16;

    const hosts = input.chilren.hosts.map((host) => {

      return {
        subject: {
          id: host.id,
          status: host.status,
          name: host.name,
          link: (id) => ['/cluster', input.id.toString(), 'host', id.toString(), 'status'],
        },
        children: [],
      };
    });

    const services = input.chilren.services.map((service) => {

      return {
        subject: {
          id: service.id,
          status: service.status,
          name: service.name,
        },
        children: service.hc.map(component => ({
          subject: {
            id: component.id,
            name: component.name,
            status: component.status,
          },
          children: component.hosts.map(host => ({
            subject: {
              id: host.id,
              status: host.status,
              name: host.name,
              link: (id) => ['/cluster', input.id.toString(), 'host', id.toString(), 'status'],
            },
            children: [],
          })),
        })),
      };
    });

    return [{
      subject: {
        id: input.id,
        status: input.status,
        name: input.name,
      },
      children: [
        {
          subject: {
            name: 'Hosts',
            status: hostsStatus
          },
          children: hosts,
        },
        {
          subject: {
            name: 'Services',
            status: servicesStatus
          },
          children: services,
        }
      ],
    }];
  }

}
