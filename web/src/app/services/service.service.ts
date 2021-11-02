import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiService } from '@app/core/api';
import { EntityService } from '@app/abstract/entity-service';
import { environment } from '@env/environment';
import { Service } from '@app/core/types';

@Injectable({
  providedIn: 'root',
})
export class ServiceService extends EntityService<Service> {

  constructor(
    protected api: ApiService,
  ) {
    super(api);
  }

  get(
    id: number,
    params: { [key: string]: string } = {},
  ): Observable<Service> {
    return this.api.get(`${environment.apiRoot}service/${id}/`, params);
  }

}
