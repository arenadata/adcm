import { Component, OnInit } from '@angular/core';
import { Job } from "@app/core/types";
import { AuthService } from "@app/core/auth/auth.service";

@Component({
  selector: 'app-download-button-column',
  templateUrl: './download-button-column.component.html',
  styleUrls: ['./download-button-column.component.scss']
})
export class DownloadButtonColumnComponent implements OnInit {

  row: Job;

  constructor(private auth: AuthService) {}

  ngOnInit(): void {}

  download() {
    const isLoggedIn = this.auth.auth;

    if (isLoggedIn) {
      location.href = `api/v1/task/${this.row?.id}/download`;
    } else {
      window.location.href = "/login";
    }
  }
}
