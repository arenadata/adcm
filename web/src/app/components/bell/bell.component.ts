import { Component, OnInit } from '@angular/core';
import { JobService } from '@app/services/job.service';
import { BaseDirective } from '@adwp-ui/widgets';

@Component({
  selector: 'app-bell',
  templateUrl: './bell.component.html',
  styleUrls: ['./bell.component.scss']
})
export class BellComponent extends BaseDirective implements OnInit {

  constructor(
    private jobService: JobService,
  ) {
    super();
  }

  ngOnInit(): void {
    this.jobService.events().pipe(this.takeUntil()).subscribe(event => console.log(event));
  }

}
