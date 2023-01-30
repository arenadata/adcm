import { Component } from '@angular/core';
import { AdwpIdentityMatcher, AdwpStringHandler } from '@app/adwp';
import { IRbacObjectCandidateServiceModel } from '../../../../../../models/rbac/rbac-object-candidate';
import { ParametrizedByDirective } from '../../directives/parametrized-by.directive';

@Component({
  selector: 'app-parametrized-by-service',
  templateUrl: './parametrized-by-service.component.html',
  styleUrls: ['./parametrized-by-service.component.scss']
})
export class ParametrizedByServiceComponent extends ParametrizedByDirective {
  roleFilter = '';

  serviceHandler: AdwpStringHandler<IRbacObjectCandidateServiceModel> = (service: IRbacObjectCandidateServiceModel) => service.name;
  serviceComparator: AdwpIdentityMatcher<IRbacObjectCandidateServiceModel> = (item1: IRbacObjectCandidateServiceModel, item2: IRbacObjectCandidateServiceModel) => (item1?.name === item2?.name);

  isError(name: string): boolean {
    const f = this.object.get(name);
    return f.invalid && (f.dirty || f.touched);
  }

  hasError(error: string): boolean {
    return this.object.hasError(error);
  }

  reset(): void {
    this.object.get('cluster').reset([]);
    this.object.get('parent').reset([]);
  }
}
