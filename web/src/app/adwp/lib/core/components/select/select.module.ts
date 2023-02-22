import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AdwpSelectComponent } from './select.component';
import { OverlayModule } from '@angular/cdk/overlay';
import { AdwpDropdownModule } from '../../directives/dropdown/dropdown.module';
import { AdwpSelectionListModule } from '../selection-list/selection-list.module';
import { AdwpClickOutsideModule } from '../../directives';
import { FormsModule } from '@angular/forms';
import { AdwpMapperPipeModule } from '../../../cdk';


@NgModule({
  declarations: [
    AdwpSelectComponent
  ],
  exports: [
    AdwpSelectComponent,
  ],
  imports: [
    CommonModule,
    OverlayModule,
    AdwpDropdownModule,
    AdwpSelectionListModule,
    AdwpClickOutsideModule,
    FormsModule,
    AdwpMapperPipeModule
  ]
})
export class AdwpSelectModule {
}
