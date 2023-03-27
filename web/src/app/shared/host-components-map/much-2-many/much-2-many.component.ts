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
import { AfterViewChecked, ChangeDetectorRef, Component, EventEmitter, Input, Output } from '@angular/core';
import { FormGroup } from '@angular/forms';
import { IActionParameter, isNumber } from '@app/core/types';
import { CompTile, HostTile, Tile } from '../types';
import { StatusType } from "@app/components/maintenance-mode-button/maintenance-mode-button.component";

@Component({
  selector: 'app-much-2-many',
  templateUrl: './much-2-many.component.html',
  styleUrls: ['./much-2-many.component.scss'],
})
export class Much2ManyComponent implements AfterViewChecked {
  isShow = false;
  statusType = StatusType;

  @Output() clickToTitleEvt: EventEmitter<any> = new EventEmitter();
  @Output() clearRelationEvt: EventEmitter<{ relation: Tile; model: Tile }> = new EventEmitter();
  @Input() model: Tile;
  @Input() form: FormGroup;
  @Input() actionParameters: IActionParameter[];
  @Input() selectedComponent: CompTile;

  constructor(private cdRef : ChangeDetectorRef) {}

  ngAfterViewChecked() {
    this.cdRef.detectChanges();
  }

  isDisabled() {
    if (this.model?.actions) return !this.model.actions.length;
    return this.model?.disabled;
  }

  isHostDisabled() {
    return this.model?.mm === this.statusType.On && !this.hasHcRelations(this.model)
  }

  isError() {
    if ('service_id' in this.model && Object.keys(this.form.controls).length) {
      const sc = this.model as CompTile;
      const control = this.form.controls[`${sc.service_id}/${sc.id}`];

      if (!control || !control?.errors?.error) return true;

      sc.notification = control.errors.error || null;
      return !control.invalid;
    }
    return true;
  }

  isMandatory() {
    if (this.model?.limit) {
      return ['+', 'odd', 1].includes(this.model?.limit[0]) && this.model?.relations.length === 0;
    }

    return false;
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
    const [a, b] = this.model.limit,
      lim = isNumber(b) ? b : a === 'odd' ? 1 : a === 'depend' ? 0 : a;
    return `${this.model.relations.length}${lim !== 0 ? ` / ${lim}` : ''}`;
  }

  tooltip() {
    if (this.isHostDisabled()) {
      return 'Host is in "Maintenance mode"';
    }

    return null;
  }

  hasHcRelations(host: HostTile): boolean {
    if (!this.selectedComponent) return false;
    if (host?.relations.length === 0 && this.selectedComponent?.actions && this.selectedComponent?.actions.includes('add')) return true;
    if (host?.relations.length === 0) return false;

    return !!host?.relations.some((relation) => relation.id === this.selectedComponent.id && this.selectedComponent?.actions && this.selectedComponent?.actions.includes('remove'));
  }
}
