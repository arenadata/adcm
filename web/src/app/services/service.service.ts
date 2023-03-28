import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiService } from '@app/core/api';
import { EntityService } from '@app/abstract/entity-service';
import { environment } from '@env/environment';
import { Service } from '@app/core/types';
import { HavingStatusTreeAbstractService } from '@app/abstract/having-status-tree.abstract.service';
import { ServiceStatusTree, StatusTree } from '@app/models/status-tree';
import { filter, switchMap } from "rxjs/operators";
import { DialogComponent } from "@app/shared/components";
import { MatDialog } from "@angular/material/dialog";

@Injectable({
  providedIn: 'root',
})
export class ServiceService extends EntityService<Service> implements HavingStatusTreeAbstractService<ServiceStatusTree, Service> {

  constructor(
    protected api: ApiService,
    public dialog: MatDialog,
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

  acceptServiceLicense(item) {
    return this.api.root
      .pipe(
        switchMap((root) =>
          this.api.get<{ text: string }>(`/api/v1/stack/prototype/${item.prototype_id}/license/`)
            .pipe(
              switchMap((info) =>
                this.dialog
                  .open(DialogComponent, {
                    data: {
                      title: `Accept license agreement ${item.service_name}`,
                      text: info.text,
                      closeOnGreenButtonCLick: true,
                      controls: {label: 'Do you accept the license agreement?', buttons: ['Yes', 'No']},
                    },
                  })
                  .beforeClosed()
                  .pipe(
                    filter((yes) => yes),
                    switchMap(() =>
                      this.api.put(`/api/v1/stack/prototype/${item.prototype_id}/license/accept/`, {}).pipe()
                    )
                  )
              )
            )
        )
      )
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
