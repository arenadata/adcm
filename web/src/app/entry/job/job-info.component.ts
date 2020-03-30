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
import { Component, Input } from '@angular/core';
import { JobStatus } from '@app/core/types';

import { ITimeInfo } from './log/log.component';

@Component({
  selector: 'app-job-info',
  template: `
    <div class="time-info">
      <div>
        <mat-icon color="primary" class="start_flag">outlined_flag</mat-icon>
        <span>{{ TimeInfo?.start }}</span>
      </div>
      <div>
        <mat-icon class="icon-locked running" *ngIf="status === 'running'; else done">autorenew</mat-icon>
        <ng-template #done>
          <i [class]="status"><mat-icon>{{ getIcon(status) }}</mat-icon></i>
        </ng-template>
        <span>{{ TimeInfo?.time }}</span>
      </div>
      <div *ngIf="TimeInfo?.end">
        <mat-icon color="primary" class="finish_flag">outlined_flag</mat-icon>
        <span>{{ TimeInfo?.end }}</span>
      </div>
    </div>
  `,
  styles: [
    `
      :host {
        position: fixed;
        right: 40px;
        top: 120px;
      }
      .time-info,
      .time-info div {
        display: flex;
        align-items: center;
      }
      .time-info div mat-icon {
        margin-right: 6px;
      }
      .time-info div span {
        margin-right: 30px;
      }
      .start_flag {
        transform: rotate(30deg);
        font-size: 20px;
        margin-top: 8px;
      }
      .finish_flag {
        transform: rotate(150deg);
        font-size: 20px;
      }
    `
  ]
})
export class JobInfoComponent {
  @Input() TimeInfo: ITimeInfo;
  @Input() status: JobStatus;
  
  getIcon(status: string) {
    switch (status) {
      case 'aborted':
        return 'block';
      default:
        return 'done_all';
    }
  }
}
