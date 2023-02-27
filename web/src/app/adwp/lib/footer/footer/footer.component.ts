import { Component, OnInit } from '@angular/core';

import { ConfigService } from '../../services/config.service';
import { IVersionInfo } from '../../models/version-info';

@Component({
  selector: 'adwp-footer',
  templateUrl: './footer.component.html',
  styleUrls: ['./footer.component.scss']
})
export class FooterComponent implements OnInit {

  currentYear = new Date().getFullYear();
  versionData: IVersionInfo;

  constructor(
    private config: ConfigService,
  ) { }

  ngOnInit(): void {
    this.versionData = this.config.getVersion(this.versionData);
  }

}
