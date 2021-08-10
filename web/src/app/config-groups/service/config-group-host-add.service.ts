import { Injectable } from '@angular/core';
import { FormModel, IAddService } from '../../shared/add-component/add-service-token';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import { ClusterService } from '../../core/services/cluster.service';
import { Host, TypeName } from '../../core/types';
import { Params } from '@angular/router';
import { Observable } from 'rxjs';
import { of } from 'rxjs/internal/observable/of';
import { ApiService } from '../../core/api';
import { environment } from '../../../environments/environment';
import { ConfigGroup } from '../model/config-group.model';
import { AddHostToConfigGroupComponent } from '@app/config-groups/components/config-group-host-add/host2configgroup.component';

const newConfigGroupHostForm = () =>
  new FormGroup({
    name: new FormControl('', Validators.required),
    description: new FormControl(),
  });

@Injectable({
  providedIn: 'root'
})
export class ConfigGroupHostAddService implements IAddService {

  get Cluster() {
    return this.cluster.Cluster;
  }

  constructor(private cluster: ClusterService, protected api: ApiService) {}

  model(name?: string): FormModel {
    return {
      name: 'host2configgroup',
      title: 'Config group hosts',
      form: newConfigGroupHostForm(),
      component: AddHostToConfigGroupComponent
    };
  }

  add(group: Partial<ConfigGroup>): Observable<any> {
    const params = { ...group };
    params.object_type = 'cluster';
    params.object_id = this.Cluster.id;
    return this.api.post<unknown>(`${environment.apiRoot}config-group/`, params);
  }

  getList<T>(type: TypeName, param: Params = {}): Observable<T[]> {
    console.log('asdasdasdasd');

    // return this.api.get<Host[]>(`${environment.apiRoot}config-group/`).pipe(
    //   map((hosts) =>
    //     hosts
    //       .map((host) => ({
    //         ...host,
    //         name: host.fqdn,
    //       }))
    //   )
    // );

    return of([]);

  }

  addHost(host: Partial<Host>): Observable<Host> {
    return of(null);
  }

}
