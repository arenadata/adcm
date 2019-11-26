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
import { Component, EventEmitter } from '@angular/core';
import { ApiService } from '@app/core/api';
import { Widget } from '@app/core/types';
import { Cluster } from '@app/core/types/api';
import { DynamicComponent, DynamicEvent } from '@app/shared/directives/dynamic.directive';
import { Observable, Subject } from 'rxjs';
import { filter, map, tap } from 'rxjs/operators';

import { ChannelService } from '../../channel.service';

interface IProp {
  key: string;
  value: string;
}

@Component({
  selector: 'app-inside',
  templateUrl: './inside.component.html',
  styleUrls: ['./inside.component.scss'],
  // changeDetection: ChangeDetectionStrategy.OnPush 
})
export class InsideComponent implements DynamicComponent {
  event = new EventEmitter<DynamicEvent>();
  model: Widget;
  cluster$: Observable<Cluster>;
  props$: Subject<IProp[]> = new Subject<IProp[]>();

  constructor(private channel: ChannelService, private api: ApiService) {
    this.cluster$ = this.channel.stream$.pipe(
      filter(data => data.cmd === 'open_details'),
      map(data => data.row as Cluster),
      tap(this.parse.bind(this))
    );
  }

  parse(cluster: Cluster): void {
    const props = Object.keys(cluster)
      .filter(key => typeof cluster[key] === 'string' && cluster[key].indexOf('http') !== -1 && key !== 'url')
      .map(key => ({ key, value: cluster[key] }));

    this.props$.next(props);
  }

  _value(prop): void {
    prop.value$ = this.api.get(prop.value);
  }

}
