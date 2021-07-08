import { Component, Input } from '@angular/core';

import { AdcmEntity } from '@app/models/entity';
import { NavItem } from '@app/shared/details/navigation.service';

@Component({
  selector: 'app-details',
  templateUrl: './details.component.html',
  styleUrls: ['./details.component.scss']
})
export class DetailsComponent {

  @Input() navigationPath: AdcmEntity[];
  @Input() title: string;
  @Input() items: NavItem[];

}
