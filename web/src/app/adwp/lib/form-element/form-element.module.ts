import { MatButtonModule } from '@angular/material/button';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AdwpInputComponent } from './input/input.component';
import { FieldDirective } from './field.directive';
import { AdwpControlsComponent } from './controls/controls.component';
import { AdwpInputSelectComponent } from './input-select/input-select.component';
import { AdwpSelectModule } from '../core';

@NgModule({
  declarations: [AdwpInputSelectComponent, AdwpInputComponent, FieldDirective, AdwpControlsComponent],
  imports: [CommonModule, FormsModule, ReactiveFormsModule, MatFormFieldModule, MatInputModule, MatButtonModule, AdwpSelectModule],
  exports: [AdwpInputSelectComponent, AdwpInputComponent, FieldDirective, AdwpControlsComponent],
})
export class AdwpFormElementModule {
}
