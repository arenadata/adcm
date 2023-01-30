import { Component, Input } from '@angular/core';
import { adwpDefaultProp, AdwpStringHandler } from '@app/adwp';
import {
  IRbacObjectCandidateClusterModel,
  IRbacObjectCandidateModel
} from '../../../../../../models/rbac/rbac-object-candidate';
import { ParametrizedByDirective } from '../../directives/parametrized-by.directive';

@Component({
  selector: 'app-parametrized-by-cluster',
  templateUrl: './parametrized-by-cluster.component.html',
  styleUrls: ['./parametrized-by-cluster.component.scss']
})
export class ParametrizedByClusterComponent extends ParametrizedByDirective {

  @Input()
  candidates: Pick<IRbacObjectCandidateModel, 'cluster'>;

  @Input()
  @adwpDefaultProp()
  isParent = false;

  clusterHandler: AdwpStringHandler<IRbacObjectCandidateClusterModel> = (cluster: IRbacObjectCandidateClusterModel) => cluster.name;

}
