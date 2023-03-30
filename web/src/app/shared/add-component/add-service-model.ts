import { EventEmitter, InjectionToken, Type } from '@angular/core';
import { FormGroup } from '@angular/forms';
import { Observable, Subscription } from 'rxjs';
import { Host, Service, StackBase, TypeName } from '@app/core/types';
import { Params } from '@angular/router';
import { BaseFormDirective } from '@app/shared/add-component/base-form.directive';
import { ICluster } from '@app/models/cluster';
import { ListResult } from '@app/models/list-result';

export const ADD_SERVICE_PROVIDER = new InjectionToken<IAddService>('AddService');

export interface FormModel<T = any> {
  name: string;
  value?: T;
  title?: string;
  form?: FormGroup;
  success?: EventEmitter<{ flag: boolean; obj: any }>;
  component?: Type<BaseFormDirective>;
  clusterId?: number;
}

export interface IAddService {
  model(name?: string): FormModel;

  Cluster: ICluster;

  Current: any;

  add?<T>(data: any, name?: TypeName, prototype?: StackBase): Observable<T>;

  get?<T>(id: number): Observable<T>;

  update?<T>(url: string, data: any): Observable<T>;

  getList?<T>(type: TypeName, param: Params): Observable<T[]>;

  addHost?(host: Partial<Host>): Observable<Host>;

  genName?(form: FormGroup): Subscription;

  addHostInCluster?(ids: number[]): Observable<unknown[]>;

  getListResults?<T>(type: TypeName, param: Params): Observable<ListResult<T>>;

  getProtoServiceForCurrentCluster?(): Observable<{ name: string, id: number, url: string, version: string, edition: string, description: string, display_name: string, license: 'unaccepted' | 'accepted' | 'absent', bundle_id: number, bundle_edition: string, selected: boolean }[]>;

  addService?(data: { prototype_id: number }[]): Observable<Service[]>;

  addServiceInCluster?(data: { prototype_id: number }[]): Observable<unknown>;
}
