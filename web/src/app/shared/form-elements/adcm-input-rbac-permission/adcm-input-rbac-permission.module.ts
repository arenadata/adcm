import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AdcmInputRbacPermissionComponent } from './adcm-input-rbac-permission.component';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatChipsModule } from '@angular/material/chips';
import {
  AdwpClickOutsideModule,
  AdwpDropdownModule,
  AdwpMapperPipeModule,
  AdwpFilterPipeModule
} from '@app/adwp';
import { MatIconModule } from '@angular/material/icon';
import { ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatInputModule } from '@angular/material/input';
import { TooltipModule } from '../../components/tooltip/tooltip.module';
import { FalseAsEmptyArrayModule } from '../../pipes/false-as-empty-array/false-as-empty-array.module';


@NgModule({
  declarations: [
    AdcmInputRbacPermissionComponent
  ],
  exports: [
    AdcmInputRbacPermissionComponent
  ],
  imports: [
    CommonModule,
    MatFormFieldModule,
    MatChipsModule,
    AdwpDropdownModule,
    MatIconModule,
    ReactiveFormsModule,
    AdwpClickOutsideModule,
    AdwpMapperPipeModule,
    MatButtonModule,
    AdwpFilterPipeModule,
    MatInputModule,
    TooltipModule,
    FalseAsEmptyArrayModule
  ]
})
export class AdcmInputRbacPermissionModule {
}
