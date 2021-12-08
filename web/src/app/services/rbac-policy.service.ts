import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { DeletableEntityAbstractService } from '@app/abstract/deletable-entity.abstract.service';
import { ApiService } from '@app/core/api';
import { environment } from '@env/environment';

@Injectable()
export class RbacPolicyService implements DeletableEntityAbstractService {

  constructor(
    protected api: ApiService,
  ) {}

  delete(id: number): Observable<unknown> {
    return this.api.delete(`${environment.apiRoot}rbac/policy/${id}/`);
  }

}
