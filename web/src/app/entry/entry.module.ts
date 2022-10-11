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
import { SharedModule } from '@app/shared/shared.module';
import { HostproviderComponent } from '@app/components/hostprovider/hostprovider.component';
import { HostListComponent } from '@app/components/host/host-list/host-list.component';
import { NameEditColumnComponent } from "@app/components/columns/name-edit-column/name-edit-column.component";
import { NameEditColumnFieldComponent } from "@app/components/columns/name-edit-column/name-edit-column-field.component";

@NgModule({
  imports: [CommonModule, SharedModule],
  declarations: [HostproviderComponent, HostListComponent, NameEditColumnComponent, NameEditColumnFieldComponent],
})
export class EntryModule {}
