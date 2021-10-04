import { ChangeDetectionStrategy, Component, Input, OnInit, TemplateRef } from '@angular/core';
import { AttributeWrapper, ConfigAttributeOptions } from '@app/shared/configuration/attributes/attribute.service';
import { AbstractControl, FormControl, FormGroup } from '@angular/forms';
import { IFieldOptions } from '@app/shared/configuration/types';

@Component({
  selector: 'app-group-keys-wrapper',
  template: `
    <div class="group-keys-wrapper">
      <div class="group-checkbox">
        <mat-checkbox [appTooltip]="wrapperOptions.tooltipText" [formControl]="groupControl"></mat-checkbox>
      </div>
      <div class="group-field">
        <ng-container *ngTemplateOutlet="fieldTemplate"></ng-container>
      </div>
    </div>
  `,
  styleUrls: ['group-keys-wrapper.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class GroupKeysWrapperComponent implements AttributeWrapper, OnInit {
  groupControl: FormControl;

  @Input() fieldTemplate: TemplateRef<any>;

  @Input() wrapperOptions: ConfigAttributeOptions;

  @Input() attributeForm: FormGroup;

  @Input() fieldOptions: IFieldOptions;

  ngOnInit(): void {
    this.groupControl = this._resolveControl(this.attributeForm, this.fieldOptions);
  }

  private _resolveControl(attributeForm: FormGroup, fieldOptions: IFieldOptions): FormControl {
    let attributeControl: AbstractControl = attributeForm;

    fieldOptions.key?.split('/').reverse().forEach((key) => attributeControl = attributeControl.get(key));

    return attributeControl as FormControl;
  }
}
