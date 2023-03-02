import { Component, Input } from '@angular/core';
import { ParametrizedByDirective } from '../../directives/parametrized-by.directive';
import {
  IRbacObjectCandidateModel,
  IRbacObjectCandidateProviderModel
} from '../../../../../../models/rbac/rbac-object-candidate';
import { AdwpStringHandler } from '@app/adwp';

@Component({
  selector: 'app-parametrized-by-provider',
  templateUrl: './parametrized-by-provider.component.html',
  styleUrls: ['./parametrized-by-provider.component.scss']
})
export class ParametrizedByProviderComponent extends ParametrizedByDirective {

  @Input()
  candidates: Pick<IRbacObjectCandidateModel, 'provider'>;

  providerHandler: AdwpStringHandler<IRbacObjectCandidateProviderModel> = (provider: IRbacObjectCandidateProviderModel) => provider.name;

}
