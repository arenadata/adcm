// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
import { CommonModule } from '@angular/common';
import { NgModule } from '@angular/core';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';

import { MaterialModule } from '../material.module';
import { StuffModule } from '../stuff.module';
import { BooleanComponent } from './boolean.component';
import { BundlesComponent } from './bundles.component';
import { ButtonUploaderComponent } from './button-uploader.component';
import { ConfirmEqualValidatorDirective } from './confirm-equal-validator.directive';
import { DropdownComponent } from './dropdown.component';
import { ErrorInfoComponent } from './error-info.component';
import { FieldDirective } from './field.directive';
import { InputComponent } from './input.component';
import { JsonComponent } from './json.component';
import { BaseMapListDirective, FieldListComponent, FieldMapComponent } from './map.component';
import { PasswordComponent } from './password/password.component';
import { TextBoxComponent } from './text-box.component';
import { TextareaComponent } from './textarea.component';
import { VariantComponent } from './variant.component';
import { SecretTextComponent } from './secret-text/secret-text.component';
import { SecretFileComponent } from './secret-file/secret-file.component';

@NgModule({
  declarations: [
    PasswordComponent,
    BooleanComponent,
    TextBoxComponent,
    TextareaComponent,
    JsonComponent,
    DropdownComponent,
    BundlesComponent,
    ButtonUploaderComponent,
    FieldListComponent,
    FieldMapComponent,
    InputComponent,
    BaseMapListDirective,
    ConfirmEqualValidatorDirective,
    FieldDirective,
    ErrorInfoComponent,
    VariantComponent,
    SecretTextComponent,
    SecretFileComponent
  ],
  imports: [CommonModule, FormsModule, ReactiveFormsModule, MaterialModule, StuffModule],
  exports: [
    FieldListComponent,
    FieldMapComponent,
    PasswordComponent,
    BooleanComponent,
    TextBoxComponent,
    TextareaComponent,
    JsonComponent,
    DropdownComponent,
    BundlesComponent,
    InputComponent,
    ButtonUploaderComponent,
    VariantComponent,
    ConfirmEqualValidatorDirective,
    SecretTextComponent,
    SecretFileComponent
  ],
})
export class FormElementsModule {}
