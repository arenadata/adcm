import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DynamicDirective } from './dynamic.directive';


@NgModule({
  declarations: [DynamicDirective],
  imports: [
    CommonModule
  ],
  exports: [DynamicDirective]
})
export class DynamicModule {
}
