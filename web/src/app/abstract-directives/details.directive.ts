import { Directive } from '@angular/core';

import { AdcmEntity } from '../models/entity';

@Directive({
  selector: '[appDirective]',
})
export abstract class DetailsDirective {

  abstract path: AdcmEntity[];
  abstract title: string;

}
