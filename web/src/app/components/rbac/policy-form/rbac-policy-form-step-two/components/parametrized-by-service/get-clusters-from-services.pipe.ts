import { Pipe, PipeTransform } from '@angular/core';
import {
  IRbacObjectCandidateModel,
  IRbacObjectCandidateServiceModel
} from '../../../../../../models/rbac/rbac-object-candidate';

@Pipe({
  name: 'getParents'
})
export class GetParentsFromServicesPipe implements PipeTransform {

  transform(service: IRbacObjectCandidateServiceModel): Pick<IRbacObjectCandidateModel, 'cluster'> {
    if (!service) {
      return null;
    }

    return {
      cluster: service.clusters
    };
  }

}
