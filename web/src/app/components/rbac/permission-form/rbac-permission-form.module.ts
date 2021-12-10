import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RbacPermissionFormComponent } from './rbac-permission-form.component';
import { AdwpFormElementModule, AdwpSelectionListModule } from '@adwp-ui/widgets';
import { ReactiveFormsModule } from '@angular/forms';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';


@NgModule({
  declarations: [
    RbacPermissionFormComponent
  ],
  imports: [
    CommonModule,
    AdwpFormElementModule,
    ReactiveFormsModule,
    MatChipsModule,
    MatDividerModule,
    AdwpSelectionListModule
  ],
  exports: [
    RbacPermissionFormComponent
  ]
})
export class RbacPermissionFormModule {
}
