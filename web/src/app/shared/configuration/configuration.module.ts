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
import { MaterialModule } from "@app/shared/material.module";
import { FormElementsModule } from '../form-elements/form-elements.module';
import { StuffModule } from '../stuff.module';
import { FieldService } from './services/field.service';
import { FieldComponent } from './field/field.component';
import { ConfigFieldsComponent } from './fields/fields.component';
import { GroupFieldsComponent } from './group-fields/group-fields.component';
import { ConfigComponent } from './main/config.component';
import { ItemComponent } from './scheme/item.component';
import { RootComponent } from './scheme/root.component';
import { SchemeComponent } from './scheme/scheme.component';
import { SchemeService } from './scheme/scheme.service';
import { ColorOptionDirective } from './tools/color-option.directive';
import { HistoryComponent } from './tools/history.component';
import { SearchComponent } from './tools/search.component';
import { ToolsComponent } from './tools/tools.component';
import { YspecService } from './yspec/yspec.service';
import { AdwpListModule } from '@adwp-ui/widgets';
import { AddingModule } from '@app/shared/add-component/adding.module';
import { ConfigService } from '@app/shared/configuration/services/config.service';
import { ConfigGroupModule } from '@app/config-groups';
import { AttributesModule } from '@app/shared/configuration/attributes/attributes.module';
import { ConfigAttributeNames } from '@app/shared/configuration/attributes/attribute.service';
import { GroupKeysWrapperComponent } from '@app/shared/configuration/attributes/attributes/group-keys/group-keys-wrapper.component';
import { FilterComponent } from "@app/shared/configuration/tools/filter/filter.component";
import { FilterListComponent } from "@app/shared/configuration/tools/filter/filter-list/filter-list.component";

@NgModule({
  declarations: [
    FieldComponent,
    ConfigFieldsComponent,
    GroupFieldsComponent,
    ConfigComponent,
    HistoryComponent,
    SearchComponent,
    FilterComponent,
    FilterListComponent,
    ColorOptionDirective,
    ToolsComponent,
    SchemeComponent,
    RootComponent,
    ItemComponent
  ],
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    StuffModule,
    FormElementsModule,
    MaterialModule,
    AdwpListModule,
    AddingModule,
    ConfigGroupModule,
    AttributesModule.forRoot({
      group_keys: {
        name: ConfigAttributeNames.GROUP_KEYS,
        wrapper: GroupKeysWrapperComponent,
        options: {
          tooltipText: 'Group parameter'
        }
      },
      custom_group_keys: {
        name: ConfigAttributeNames.CUSTOM_GROUP_KEYS,
        options: {
          tooltipText: 'This parameter can not be added to config group'
        }
      }
    }),
  ],
  exports: [ConfigComponent, ConfigFieldsComponent, FilterComponent, FilterListComponent],
  providers: [FieldService, YspecService, SchemeService, ConfigService],
})
export class ConfigurationModule {
}
