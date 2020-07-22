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
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatToolbarModule } from '@angular/material/toolbar';
import { RouterModule } from '@angular/router';

import { StuffModule } from '../stuff.module';
import { DetailComponent } from './detail.component';
import { LeftComponent } from './left/left.component';
import { NavigationService } from './navigation.service';
import { SubtitleComponent } from './subtitle.component';
import { TopComponent } from './top/top.component';

@NgModule({
  imports: [CommonModule, RouterModule, StuffModule, MatCardModule, MatToolbarModule, MatSidenavModule, MatListModule, MatIconModule],
  exports: [DetailComponent],
  declarations: [DetailComponent, SubtitleComponent, LeftComponent, TopComponent],
  providers: [NavigationService],
})
export class DetailsModule {}
