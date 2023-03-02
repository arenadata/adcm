import { Component, Input } from '@angular/core';
import { ParametrizedByDirective } from '../../directives/parametrized-by.directive';
import {
  IRbacObjectCandidateHostModel,
  IRbacObjectCandidateModel
} from '../../../../../../models/rbac/rbac-object-candidate';
import { AdwpStringHandler } from '@app/adwp';

@Component({
  selector: 'app-parametrized-by-host',
  templateUrl: './parametrized-by-host.component.html',
  styleUrls: ['./parametrized-by-host.component.scss']
})
export class ParametrizedByHostComponent extends ParametrizedByDirective {

  @Input()
  candidates: Pick<IRbacObjectCandidateModel, 'host'>;

  hostHandler: AdwpStringHandler<IRbacObjectCandidateHostModel> = (host: IRbacObjectCandidateHostModel) => host.name;
}
