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
import { RouterModule } from '@angular/router';

import { MaterialModule } from '../material.module';
import { StuffModule } from '../stuff.module';
import { HolderDirective } from './holder.directive';
import { Much2ManyComponent } from './much-2-many/much-2-many.component';
import { ServiceHostComponent } from './services2hosts/service-host.component';
import { TakeService } from './take.service';

@NgModule({
  declarations: [HolderDirective, ServiceHostComponent, Much2ManyComponent],
  imports: [CommonModule, MaterialModule, RouterModule, StuffModule],
  exports: [ServiceHostComponent],
  providers: [TakeService]
})
export class HostComponentsMapModule {}
