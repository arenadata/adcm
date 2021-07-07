import { Component, Input, OnInit } from '@angular/core';

import { AdcmEntity } from '@app/models/entity';

@Component({
  selector: 'app-details',
  templateUrl: './details.component.html',
  styleUrls: ['./details.component.scss']
})
export class DetailsComponent implements OnInit {

  @Input() navigationPath: AdcmEntity[];
  @Input() title: string;

  constructor() { }

  ngOnInit(): void {
  }

}
