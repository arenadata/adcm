// Licensed under the Apache License, Version 2.0 (the "License");
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
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

import { ClusterService } from '@app/core/services/cluster.service';

@Component({
  selector: 'app-main-info',
  template: '<div [innerHTML]="value"></div>',
  styles: [':host {padding: 0 20px;}'],
})
export class MainInfoComponent implements OnInit {
  value: SafeHtml;
  constructor(private service: ClusterService, private sanitizer: DomSanitizer) {}
  ngOnInit() {
    this.service.getMainInfo().subscribe((value) => (this.value = this.sanitizer.bypassSecurityTrustHtml(value)));
  }
}
