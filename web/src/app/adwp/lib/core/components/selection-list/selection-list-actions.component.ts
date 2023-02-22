import { Component, EventEmitter, Input, Output } from '@angular/core';
import { MatSelectionList } from '@angular/material/list';
import { MatPseudoCheckboxState } from '@angular/material/core/selection/pseudo-checkbox/pseudo-checkbox';

@Component({
  selector: 'adwp-selection-list-actions',
  templateUrl: 'selection-list-actions.component.html',
})
export class SelectionListActionsComponent {
  @Input()
  list: MatSelectionList;

  @Output()
  filterChange: EventEmitter<string> = new EventEmitter<string>();

  filter: string = '';

  get disabled(): boolean {
    return !this.list?.options?.length;
  }

  get selectAllState(): MatPseudoCheckboxState {
    return (this.list?.options?.length && this.list?.selectedOptions.selected.length === this.list?.options?.length)
      ? 'checked' : 'unchecked';
  }

  toggleOptions(selectionList: MatSelectionList): void {
    if (!this.disabled) {
      const selected = selectionList.selectedOptions.selected;
      const options = selectionList.options;

      if (options?.length > selected?.length) {
        selectionList.selectAll();
      } else {
        selectionList.deselectAll();
      }

      selectionList._emitChangeEvent(options.toArray());
    }
  }

  clear(e: MouseEvent): void {
    e.stopPropagation();
    e.preventDefault();

    this.filter = '';
    this.filterChange.emit('');
  }
}
