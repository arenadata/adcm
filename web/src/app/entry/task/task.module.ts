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
import { RouterModule, Routes } from '@angular/router';
import { AuthGuard } from '@app/core';
import { SharedModule } from '@app/shared/shared.module';

import { HoverDirective } from './hover.directive';
import { TasksComponent } from './tasks.component';
import { TaskObjectsComponent } from '@app/components/columns/task-objects/task-objects.component';
import { ObjectLinkColumnPipe } from '@app/pipes/object-link-column.pipe';
import { SortObjectsPipe } from '@app/pipes/sort-objects.pipe';
import { TaskStatusColumnComponent } from '@app/components/columns/task-status-column/task-status-column.component';
import { JobsComponent } from '@app/components/task/jobs/jobs.component';
import { JobStatusColumnComponent } from '@app/components/columns/job-status-column/job-status-column.component';
import { TaskNameComponent } from '@app/components/columns/task-name/task-name.component';

const routes: Routes = [
  {
    path: '',
    canActivate: [AuthGuard],
    component: TasksComponent
  }
];

@NgModule({
  imports: [
    CommonModule,
    SharedModule,
    RouterModule.forChild(routes),
  ],
  declarations: [
    TasksComponent,
    HoverDirective,
    TaskObjectsComponent,
    ObjectLinkColumnPipe,
    SortObjectsPipe,
    TaskStatusColumnComponent,
    TaskNameComponent,
    JobsComponent,
    JobStatusColumnComponent,
  ],
})
export class TaskModule {}
