import { Directive } from '@angular/core';
import { Observable } from 'rxjs';

import { AdcmEntity } from '../models/entity';
import { NavItem } from '../shared/details/navigation.service';
import { DetailAbstractDirective } from './detail.abstract.directive';

@Directive({
  selector: '[appDetails]',
})
export abstract class DetailsDirective extends DetailAbstractDirective {

  abstract title: string;
  abstract items: NavItem[];

  path: Observable<AdcmEntity[]>;

}
