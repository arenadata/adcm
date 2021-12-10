import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AdcmInputRbacPermissionComponent } from './adcm-input-rbac-permission.component';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatChipsModule } from '@angular/material/chips';
import { AdwpClickOutsideModule, AdwpDropdownModule, AdwpMapperPipeModule } from '@adwp-ui/widgets';
import { MatIconModule } from '@angular/material/icon';
import { ReactiveFormsModule } from '@angular/forms';


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
    AdwpMapperPipeModule
  ]
})
export class AdcmInputRbacPermissionModule {
}
