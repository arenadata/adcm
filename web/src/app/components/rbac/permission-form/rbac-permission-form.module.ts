import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RbacPermissionFormComponent } from './rbac-permission-form.component';
import { AdwpFormElementModule, AdwpSelectionListModule, AdwpFilterPipeModule } from '@app/adwp';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { MatButtonModule } from '@angular/material/button';
import { FalseAsEmptyArrayModule } from '../../../shared/pipes/false-as-empty-array/false-as-empty-array.module';


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
    AdwpSelectionListModule,
    FormsModule,
    MatButtonModule,
    AdwpFilterPipeModule,
    FalseAsEmptyArrayModule
  ],
  exports: [
    RbacPermissionFormComponent
  ]
})
export class RbacPermissionFormModule {
}
