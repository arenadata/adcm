import { Component, OnInit } from '@angular/core';
import { AuthService } from "@app/core/auth/auth.service";

@Component({
  selector: 'app-download-button-column',
  templateUrl: './download-button-column.component.html',
  styleUrls: ['./download-button-column.component.scss']
})
export class DownloadButtonColumnComponent implements OnInit {

  url: string;
  tooltip: string;

  constructor(private auth: AuthService) {}

  ngOnInit(): void {}

  download() {
    location.href = this.url;
  }
}
