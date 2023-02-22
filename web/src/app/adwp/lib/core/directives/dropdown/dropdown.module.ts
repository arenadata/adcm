import { NgModule } from '@angular/core';

import { AdwpDropdownDirective } from './dropdown.directive';
import { AdwpDropdownBoxModule } from '../../components/dropdown-box/dropdown-box.module';

@NgModule({
  imports: [AdwpDropdownBoxModule],
  declarations: [AdwpDropdownDirective],
  exports: [AdwpDropdownDirective],
})
export class AdwpDropdownModule {
}
