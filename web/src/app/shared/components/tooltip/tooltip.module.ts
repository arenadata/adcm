import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SimpleTextComponent, TooltipComponent } from './tooltip.component';
import { TooltipDirective } from './tooltip.directive';


@NgModule({
  declarations: [TooltipComponent, SimpleTextComponent, TooltipDirective],
  imports: [
    CommonModule
  ],
  exports: [TooltipComponent, SimpleTextComponent, TooltipDirective]
})
export class TooltipModule {
}
