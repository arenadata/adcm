import { Injectable } from '@angular/core';
import { FormModel, IAddService } from '../../shared/add-component/add-service-token';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import { ClusterService } from '../../core/services/cluster.service';
import { Host, TypeName } from '../../core/types';
import { Params } from '@angular/router';
import { Observable } from 'rxjs';
import { of } from 'rxjs/internal/observable/of';
import { AddConfigGroupComponent } from '../components/config-group-add/config-group-add.component';

const newConfigGroupForm = () =>
  new FormGroup({
    name: new FormControl('', Validators.required),
    description: new FormControl(),
  });

@Injectable({
  providedIn: 'root'
})
export class ConfigGroupAddService implements IAddService {

  get Cluster() {
    return this.cluster.Cluster;
  }

  constructor(private cluster: ClusterService) {}

  model(name?: string): FormModel {
    return {
      name: 'configgroup',
      title: 'Config group',
      form: newConfigGroupForm(),
      component: AddConfigGroupComponent
    };
  }

  getList<T>(type: TypeName, param: Params = {}): Observable<T[]> {
    return of([]);
  }

  addHost(host: Partial<Host>): Observable<Host> {
    return of(null);
  }

}
