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
    `,
  ],
  template: `
    <div class="time-info">
      <div>
        <mat-icon color="primary" class="start_flag">outlined_flag</mat-icon>
        <span>{{ timeInfo?.start }}</span>
      </div>
      <div>
        <mat-icon *ngIf="isRun" class="icon-locked running">autorenew</mat-icon>
        <mat-icon *ngIf="!isRun" [class]="status">{{ Icon(status) }}</mat-icon>
        <span>{{ timeInfo?.time }}</span>
      </div>
      <div *ngIf="timeInfo?.end">
        <mat-icon color="primary" class="finish_flag">outlined_flag</mat-icon>
        <span>{{ timeInfo?.end }}</span>
      </div>
    </div>
  `,
})
export class JobInfoComponent {
  @Input() timeInfo: ITimeInfo;
  @Input() status: JobStatus;
  Icon = (status: string): string => (status === 'aborted' ? 'block' : 'done_all');
  get isRun(): boolean {
    return this.status === 'running';
  }
}
