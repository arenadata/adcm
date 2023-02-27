import { Component, EventEmitter, Inject, Injector, OnInit, Type } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';

import { ComponentData } from './ComponentData';

/**
 * The 'abstract' component displayed in the dialog
 * @template T the model passed to the component
 */
export interface AdwpDynamicComponent<T = any> {
  emitter?: EventEmitter<T>;
  model: T;
  onEnterKey?: () => void;
}

export interface DialogData {
  title: string;
  component: Type<AdwpDynamicComponent>;
  model?: any;
  emitter?: EventEmitter<any>;
  text?: string;
  controls?: any[] | any;
  disabled?: boolean;
}

@Component({
  selector: 'adwp-dialog',
  templateUrl: './dialog.component.html',
  styleUrls: ['./dialog.component.scss'],
})
export class AdwpDialogComponent implements OnInit {
  CurrentComponent: Type<AdwpDynamicComponent>;
  componentInjector: Injector;

  constructor(
    public dialogRef: MatDialogRef<AdwpDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: DialogData,
    private parentInjector: Injector
  ) {}

  ngOnInit(): void {
    this.buildComponent();
  }

  buildComponent(): void {
    if (!this.data.component) {
      return;
    }

    this.CurrentComponent = this.data.component;
    const { model, emitter } = this.data;
    this.componentInjector = Injector.create({
      providers: [
        {
          provide: ComponentData,
          useValue: {
            model,
            emitter,
          },
          deps: [],
        },
      ],
      parent: this.parentInjector,
    });
  }

  noClick(): void {
    this.dialogRef.close();
  }

  controlsIsArray(): boolean {
    return Array.isArray(this.data.controls);
  }
}
