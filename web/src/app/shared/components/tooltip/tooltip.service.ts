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
import { ApiBase, TypeName } from '@app/core/types/api';
import { EventEmitter } from 'events';
import { Subject } from 'rxjs';

export type ComponentName = 'issue' | 'status' | undefined;
export type PositionType = 'top' | 'right' | 'bottom' | 'left';
export interface TooltipOptions {
  event: MouseEvent;
  source: HTMLElement;
  options: TooltipDisplayOptions;
}

export interface TooltipDisplayOptions {
  content: string | ApiBase;
  componentName: ComponentName;
  position: PositionType;
  condition: boolean;
}

@Injectable()
export class ComponentData {
  typeName: TypeName;
  current: ApiBase;
  emitter: EventEmitter;
}

@Injectable({
  providedIn: 'root'
})
export class TooltipService {
  private positionSource = new Subject<TooltipOptions>();
  position$ = this.positionSource.asObservable();
  source: HTMLElement;

  show(event: MouseEvent, source: HTMLElement, options: TooltipDisplayOptions) {
    if (this.isShow(source, options)) {
      this.positionSource.next({ event, source, options });
      this.source = source;
    }
  }

  /**
   * TODO: show a tooltip if there is a condition
   *
   * @returns
   * @memberof TooltipComponent
   */
  isShow(source: HTMLElement, options: TooltipDisplayOptions) {
    if (options.condition) {
      return source.offsetWidth !== source.scrollWidth;
    }
    return true;
  }

  hide() {
    this.positionSource.next();
  }
}
