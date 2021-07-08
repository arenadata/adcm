import { Directive } from '@angular/core';
import { BaseDirective } from '@adwp-ui/widgets';
import { Observable } from 'rxjs';

import { AdcmEntity } from '../models/entity';
import { NavItem } from '../shared/details/navigation.service';

@Directive({
  selector: '[appDirective]',
})
export abstract class DetailsDirective extends BaseDirective {

  abstract title: string;
  abstract items: NavItem[];

  path: Observable<AdcmEntity[]>;

}
