import { Injectable } from '@angular/core';
import { FormModel, IAddService } from '../../shared/add-component/add-service-token';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import { ClusterService } from '../../core/services/cluster.service';
import { Host, TypeName } from '../../core/types';
import { convertToParamMap, Params } from '@angular/router';
import { forkJoin, Observable } from 'rxjs';
import { ApiService } from '../../core/api';
import { environment } from '../../../environments/environment';
import { AddHostToConfigGroupComponent } from '@app/config-groups/components/config-group-host-add/host2configgroup.component';
import { map } from 'rxjs/operators';

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
    return this.service.Cluster;
  }

  get Current() {
    return this.service.Current;
  }

  constructor(private service: ClusterService, protected api: ApiService) {}

  model(name?: string): FormModel {
    return {
      name: 'host2configgroup',
      title: 'Config group hosts',
      form: newConfigGroupHostForm(),
      component: AddHostToConfigGroupComponent
    };
  }

  add(data: { host: number, group: number }[]): Observable<any> {
    return forkJoin(data.map((o) => this.api.post<unknown>(`${environment.apiRoot}host-group/`, o)));
  }

  getList(type: TypeName, param: Params = {}): Observable<any[]> {
    const paramMap = convertToParamMap(param);

    return this.api.getList<Host>(`${environment.apiRoot}host/`, paramMap).pipe(
      map(({ results }) => results.map((host) => ({ ...host, name: host.fqdn })))
    );
  }

}
