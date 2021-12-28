import { Injectable } from '@angular/core';
import { EntityAbstractService } from '../abstract/entity.abstract.service';
import { Observable } from 'rxjs';
import { IRbacObjectCandidateModel } from '../models/rbac/rbac-object-candidate';
import { environment as env } from '@env/environment';
import { ApiService } from '@app/core/api';


@Injectable()
export class RbacObjectCandidateService implements EntityAbstractService {
  constructor(protected api: ApiService) {}

  get(id: number): Observable<IRbacObjectCandidateModel> {
    return this.api.get(`${env.apiUI}rbac/role/${id}/object_candidate/`);
  }

}
