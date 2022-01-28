import { Directive, Input } from '@angular/core';
import { FormGroup } from '@angular/forms';
import { IRbacObjectCandidateModel } from '../../../../../models/rbac/rbac-object-candidate';
import { adwpDefaultProp, BaseDirective } from '@adwp-ui/widgets';

@Directive({
  selector: 'parametrizedBy'
})
export class ParametrizedByDirective extends BaseDirective {

  @Input()
  @adwpDefaultProp()
  object: FormGroup | null = null;

  @Input()
  @adwpDefaultProp()
  candidates: Partial<IRbacObjectCandidateModel> | null = null;

}
