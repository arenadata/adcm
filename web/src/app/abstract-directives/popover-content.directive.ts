import { Directive } from '@angular/core';
import { BaseDirective } from '@app/adwp';

import { PopoverInput } from '../directives/popover.directive';

export type PopoverEventFunc = (event: any) => void;

@Directive({
  selector: '[appAbstractPopoverContent]',
})
export abstract class PopoverContentDirective extends BaseDirective {

  abstract data: PopoverInput;

  event?: PopoverEventFunc;

}
