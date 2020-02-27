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
import { Component, OnInit } from '@angular/core';
import { ClusterService } from '@app/core';
import { EventMessage, SocketState } from '@app/core/store';
import { Job, JobStatus } from '@app/core/types';
import { SocketListenerDirective } from '@app/shared';
import { Store } from '@ngrx/store';

@Component({
  selector: 'app-job-info',
  template: `
    <div class="time-info">
      <div>
        <mat-icon color="primary" style="transform:rotate(30deg);font-size: 20px;margin-top: 8px;">outlined_flag</mat-icon>
        <span>{{ dataTime.start }}</span>
      </div>
      <div>
        <mat-icon class="icon-locked running" *ngIf="status === 'running'; else done">autorenew</mat-icon>
        <ng-template #done>
          <i [class]="status"><mat-icon>{{ getIcon(status) }}</mat-icon></i>
        </ng-template>
        <span>{{ dataTime.time }}</span>
      </div>
      <div *ngIf="dataTime.end">
        <mat-icon color="primary" style="transform:rotate(150deg);font-size: 20px;">outlined_flag</mat-icon>
        <span>{{ dataTime.end }}</span>
      </div>
    </div>
  `,
  styles: [
    ':host {position: fixed; right: 40px;top: 120px;}',
    '.time-info, .time-info div {display: flex;align-items: center;}',
    '.time-info div mat-icon {margin-right: 6px;}',
    '.time-info div span {margin-right: 30px;}'
  ]
})
export class JobInfoComponent extends SocketListenerDirective implements OnInit {
  dataTime: { start: string; end: string; time: string };
  status: JobStatus;
  constructor(private service: ClusterService, protected store: Store<SocketState>) {
    super(store);
  }
  ngOnInit(): void {
    this.status = (this.service.Current as Job).status;
    this.dataTime = this.service.getOperationTimeData();
    this.startListenSocket();
  }

  getIcon(status: string) {
    switch (status) {
      case 'aborted':
        return 'block';
      default:
        return 'done_all';
    }
  }

  socketListener(m: EventMessage) {
    if (m && m.object && m.object.type === 'job' && m.object.id === this.service.Current.id) {
      this.status = m.object.details.value as JobStatus;
      const job = this.service.Current as Job;
      job.status = this.status;
      job.finish_date = new Date().toISOString();
      this.dataTime = this.service.getOperationTimeData();
    }
  }
}
