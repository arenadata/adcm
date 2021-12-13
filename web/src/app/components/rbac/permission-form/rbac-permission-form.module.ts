import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RbacPermissionFormComponent } from './rbac-permission-form.component';
import { AdwpFormElementModule, AdwpSelectionListModule, PuiFilterPipeModule } from '@adwp-ui/widgets';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { MatButtonModule } from '@angular/material/button';


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
    PuiFilterPipeModule
  ],
  exports: [
    RbacPermissionFormComponent
  ]
})
export class RbacPermissionFormModule {
}
