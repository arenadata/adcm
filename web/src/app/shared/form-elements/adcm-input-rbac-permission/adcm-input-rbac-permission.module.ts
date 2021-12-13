import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AdcmInputRbacPermissionComponent } from './adcm-input-rbac-permission.component';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatChipsModule } from '@angular/material/chips';
import {
  AdwpClickOutsideModule,
  AdwpDropdownModule,
  AdwpMapperPipeModule,
  PuiFilterPipeModule
} from '@adwp-ui/widgets';
import { MatIconModule } from '@angular/material/icon';
import { ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatInputModule } from '@angular/material/input';
import { TooltipModule } from '../../components/tooltip/tooltip.module';


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
    PuiFilterPipeModule,
    MatInputModule,
    TooltipModule
  ]
})
export class AdcmInputRbacPermissionModule {
}
