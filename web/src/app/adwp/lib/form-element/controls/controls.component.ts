import { Component, ElementRef, EventEmitter, Input, Output, ViewChild } from '@angular/core';

@Component({
  selector: 'adwp-controls',
  templateUrl: './controls.component.html',
  styleUrls: ['./controls.component.scss'],
})
export class AdwpControlsComponent {
  @Input() title = 'Create';
  @Input() disabled: boolean;
  @Input() hiddenSaveButton: boolean;
  @Output() cancel = new EventEmitter();
  @Output() save = new EventEmitter();

  @ViewChild('btn', { static: true, read: ElementRef }) saveBtn: ElementRef;

  oncancel(): void {
    this.cancel.emit();
  }

  onsave(): void {
    this.save.emit();
  }
}
