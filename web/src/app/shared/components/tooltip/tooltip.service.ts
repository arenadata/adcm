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
import { Injectable } from '@angular/core';
import { Subject } from 'rxjs';
import { ApiBase, TypeName } from '@app/core/types/api';
import { EventEmitter } from 'events';

export type ComponentName = 'issue' | 'status';
export interface TooltipOptions {
  event: MouseEvent;
  content: string | ApiBase;
  source: HTMLElement;
  componentName: ComponentName;
}

@Injectable()
export class ComponentData {
  typeName: TypeName;
  current: ApiBase;
  emitter: EventEmitter;
}

@Injectable({
  providedIn: 'root',
})
export class TooltipService {
  private positionSource = new Subject<TooltipOptions>();
  position$ = this.positionSource.asObservable();

  constructor() {}

  show(event: MouseEvent, content: string | ApiBase, source: HTMLElement, componentName: ComponentName) {
    this.positionSource.next({ event, content, source, componentName });
  }

  hide() {
    this.positionSource.next();
  }
}
