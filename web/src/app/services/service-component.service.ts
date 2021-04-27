import { Injectable } from '@angular/core';

import { ApiService } from '../core/api';
import { Observable } from 'rxjs';
import { IServiceComponent } from '../models/service-component';

@Injectable({
  providedIn: 'root',
})
export class ServiceComponentService {

  constructor(
    private api: ApiService,
  ) {}

  get(
    id: number,
    params: { [key: string]: string } = {},
  ): Observable<IServiceComponent> {
    return this.api.get(`api/v1/component/${id}`, params);
  }

}
