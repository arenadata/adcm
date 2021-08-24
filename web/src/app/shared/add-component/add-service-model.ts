import { EventEmitter, InjectionToken, Type } from '@angular/core';
import { FormGroup } from '@angular/forms';
import { Observable, Subscription } from 'rxjs';
import { Cluster, Host, Service, TypeName } from '@app/core/types';
import { Params } from '@angular/router';
import { BaseFormDirective } from '@app/shared/add-component/base-form.directive';

export const ADD_SERVICE_PROVIDER = new InjectionToken<IAddService>('AddService');

export interface FormModel {
  name: string;
  title?: string;
  form?: FormGroup;
  success?: EventEmitter<{ flag: boolean; obj: any }>;
  component?: Type<BaseFormDirective>;
}

export interface IAddService {
  model(name?: string): FormModel;

  Cluster: Cluster;

  Current: any;

  add?<T>(data: any, name?: TypeName): Observable<T>;

  getList?<T>(type: TypeName, param: Params): Observable<T[]>;

  addHost?(host: Partial<Host>): Observable<Host>;

  genName?(form: FormGroup): Subscription;

  addHostInCluster?(ids: number[]): Observable<unknown[]>;

  getListResults?<T>(type: TypeName, param: Params);

  getProtoServiceForCurrentCluster?(): Observable<{ name: string, id: number, url: string, version: string, edition: string, description: string, display_name: string, license: 'unaccepted' | 'accepted' | 'absent', bundle_id: number, bundle_edition: string, selected: boolean }[]>;

  addService?(data: { prototype_id: number }[]): Observable<Service[]>;
}
