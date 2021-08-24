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
import { FormElementsModule } from '@app/shared/form-elements/form-elements.module';
import { MaterialModule } from '@app/shared/material.module';
import { StuffModule } from '@app/shared/stuff.module';

import { AddButtonComponent } from './add-button.component';
import { AddFormComponent } from './add-form.component';
import { BaseFormDirective } from './base-form.directive';
import { ClusterComponent } from './cluster.component';
import { HostComponent } from './host.component';
import { Host2clusterComponent } from './host2cluster.component';
import { ProviderComponent } from './provider.component';
import { ServiceComponent } from './service.component';
import { ControlsComponent } from './controls.component';

@NgModule({
  declarations: [
    AddButtonComponent,
    AddFormComponent,
    ClusterComponent,
    HostComponent,
    Host2clusterComponent,
    ProviderComponent,
    ServiceComponent,
    BaseFormDirective,
    ControlsComponent,
  ],
  imports: [CommonModule, MaterialModule, StuffModule, FormsModule, ReactiveFormsModule, FormElementsModule],
  exports: [
    AddButtonComponent,
    ProviderComponent,
    ClusterComponent,
    HostComponent,
    ServiceComponent,
    Host2clusterComponent,
    BaseFormDirective,
    ControlsComponent,
  ],
  entryComponents: [AddFormComponent]
})
export class AddingModule {
}
