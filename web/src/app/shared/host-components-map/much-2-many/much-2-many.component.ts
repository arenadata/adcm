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
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { FormGroup } from '@angular/forms';
import { isNumber } from '@app/core/types';

import { CompTile, Tile } from '../types';

@Component({
  selector: 'app-much-2-many',
  templateUrl: './much-2-many.component.html',
  styleUrls: ['./much-2-many.component.scss'],
})
export class Much2ManyComponent {
  isShow = false;

  @Output() clickToTitleEvt: EventEmitter<any> = new EventEmitter();
  @Output() clearRelationEvt: EventEmitter<{ relation: Tile; model: Tile }> = new EventEmitter();
  @Input() model: Tile;
  @Input() form: FormGroup;

  isDisabled() {
    if (this.model.actions) return !this.model.actions.length;
    return this.model.disabled;
  }

  isError() {
    if ('service_id' in this.model && Object.keys(this.form.controls).length) {
      const sc = this.model as CompTile;
      const control = this.form.controls[`${sc.service_id}/${sc.id}`];
      if (!control) return false;
      sc.notification = control.errors?.error;
      return control.invalid;
    } else return false;
  }

  clearDisabled(rel: Tile) {
    if (this.model.actions) return this.model.actions.every((e) => e !== 'remove');
    return rel.disabled || this.model.disabled;
  }

  clickToTitle() {
    this.clickToTitleEvt.emit(this.model);
  }

  toggleRelations() {
    this.isShow = !this.isShow;
  }

  clearRelation(relation: Tile) {
    this.model.relations = this.model.relations.filter((a) => a !== relation);
    this.clearRelationEvt.emit({ relation, model: this.model });
  }

  setNotify() {
    const [a, b, c] = this.model.limit,
      lim = isNumber(b) ? b : a === 'odd' ? 1 : a === 'depend' ? 0 : a;
    return `${this.model.relations.length}${lim !== 0 ? ` / ${lim}` : ''}`;
  }
}
