import { Injectable } from '@angular/core';

import { ApiService } from '../core/api';
import { Observable } from 'rxjs';
import { IClusterService } from '@app/models/cluster-service';

@Injectable({
  providedIn: 'root',
})
export class ServiceService {

  constructor(
    private api: ApiService,
  ) {}

  get(
    id: number,
    params: { [key: string]: string } = {},
  ): Observable<IClusterService> {
    return this.api.get(`api/v1/service/${id}/`, params);
  }

}
