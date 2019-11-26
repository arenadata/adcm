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
import { Component, Input, OnInit } from '@angular/core';
import { ApiService } from '@app/core/api';
import { Cluster, HostComponent } from '@app/core/types';

interface Item {
  id: number;
  name: string;
}

interface Service extends Item {
  components: Item[];
}

interface Hosts extends Item {
  services: Service[];
}

@Component({
  selector: 'app-wizard-map',
  template: `
    <div class="hosts">
      <div *ngFor="let h of hosts">
        <p>
          <mat-icon>storage</mat-icon><label>{{ h.name }}</label>
        </p>
        <div class="services">
          <div *ngFor="let s of h.services">
            <p>
              <mat-icon>perm_data_setting</mat-icon><label>{{ s.name }}</label>
            </p>
            <div *ngFor="let c of s.components" class="component">
              <p>
                <mat-icon>settings_applications</mat-icon> <label>{{ c.name }}</label>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [
    '.hosts {display: flex;}',
    '.hosts > div { margin: 0 10px; box-shadow: inset 2px 2px 5px rgba(90, 90, 90, 0.5), 1px 1px 5px #383838; padding: 6px 10px;}',
    'p mat-icon { margin-right: 8px; vertical-align: bottom;}',
    '.services, .component  { margin-left: 20px;}',
  ],
})
export class MapComponent implements OnInit {
  services: Service[];
  hosts: Hosts[];

  @Input() cluster: Cluster;

  constructor(private api: ApiService) {}

  ngOnInit() {
    this.api.get<HostComponent[]>(this.cluster.hostcomponent).subscribe(hcm => this.onLoad(hcm));
  }

  public onLoad(hcm: HostComponent[]) {
    const getComponents = (sid: number) =>
      hcm
        .filter(a => a.service_id === sid)
        .map(b => ({ name: b.component_display_name || b.component, id: b.component_id }))
        .reduce((p, c) => (p.some(a => a.id === c.id) ? p : [...p, c]), []);

    const getServices = (id: number) =>
      hcm
        .filter(a => a.host_id === id)
        .map(b => ({
          id: b.service_id,
          name: b.service_display_name || b.service_name,
          components: getComponents(b.service_id),
        }))
        .reduce((p, c) => (p.some(a => a.id === c.id) ? p : [...p, c]), []);

    this.hosts = hcm
      .map(a => ({ id: a.host_id, name: a.host, services: getServices(a.host_id) }))
      .reduce((p, c) => (p.some(a => a.id === c.id) ? p : [...p, c]), []);
  }
}
