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
import { SocketListener } from '@app/shared';
import { Store } from '@ngrx/store';

@Component({
  selector: 'app-job-info',
  template: `
    <table>
      <tr>
        <th>Status</th>
        <th>Start date</th>
        <th>Finish date</th>
        <th>Time taken</th>
      </tr>
      <tr>
        <td>
          <span [class]="status">{{ status }}</span>
        </td>
        <td>{{ dataTime.start }}</td>
        <td>{{ dataTime.end }}</td>
        <td>{{ dataTime.time }}</td>
      </tr>
    </table>
  `,
  styles: [
    'table {width: 380px; margin-top: 10px;}',
    'td {padding: 6px 14px;text-align: center; white-space: nowrap;}',
    // tslint:disable-next-line: no-unused-css
    'th:first-child, td:first-child {text-align:left;padding-left: 0;}',
  ],
})
export class JobInfoComponent extends SocketListener implements OnInit {
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
