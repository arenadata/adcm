import { Component } from '@angular/core';
import { AdwpCellComponent, ILinkColumn } from '@adwp-ui/widgets';

import { Job } from '@app/core/types';

@Component({
  selector: 'app-job-name',
  template: `
    <div class="job-name-container">
      <ng-container *ngIf="row.status === 'created'; else link">
        <span class="regular-name">{{ row.display_name || row.id }}</span>
      </ng-container>
      <ng-template #link>
        <adwp-link-cell
          [row]="row"
          [column]="linkColumn"
        ></adwp-link-cell>
      </ng-template>
    </div>
  `,
  styleUrls: ['./job-name.component.scss']
})
export class JobNameComponent implements AdwpCellComponent<Job> {

  row: Job;

  linkColumn: ILinkColumn<Job> = {
    label: '',
    type: 'link',
    value: (row) => row.display_name || row.id,
    url: (row) => `/job/${row.id}`,
  };

}
