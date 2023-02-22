import { NgModule } from '@angular/core';
import { PolymorpheusModule } from '@tinkoff/ng-polymorpheus';
import { AdwpDropdownBoxComponent } from './dropdown-box.component';

@NgModule({
  imports: [
    PolymorpheusModule
  ],
  declarations: [AdwpDropdownBoxComponent],
  exports: [AdwpDropdownBoxComponent],
})
export class AdwpDropdownBoxModule {
}
