import { ChangeDetectionStrategy, Component, Input, OnInit, TemplateRef } from '@angular/core';
import {
  AttributeService,
  AttributeWrapper,
  ConfigAttributeNames,
  ConfigAttributeOptions
} from '@app/shared/configuration/attributes/attribute.service';
import { AbstractControl, FormControl, FormGroup } from '@angular/forms';
import { IFieldOptions } from '@app/shared/configuration/types';

@Component({
  selector: 'app-group-keys-wrapper',
  template: `
    <div class="group-keys-wrapper">
      <div class="group-checkbox">
        <mat-checkbox [appTooltip]="tooltipText" [formControl]="groupControl"></mat-checkbox>
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
  tooltipText: string = '';
  groupControl: FormControl;

  @Input() fieldTemplate: TemplateRef<any>;

  @Input() wrapperOptions: ConfigAttributeOptions;

  @Input() attributeForm: FormGroup;

  @Input() fieldOptions: IFieldOptions;

  constructor(private _attributeSrv: AttributeService) {
  }


  ngOnInit(): void {
    this.groupControl = this._resolveAndSetupControl(this.attributeForm, this.fieldOptions);
  }

  private _resolveAndSetupControl(attributeForm: FormGroup, fieldOptions: IFieldOptions): FormControl {
    let attributeControl: AbstractControl = attributeForm;
    let disabled = this._attributeSrv.attributes.get(ConfigAttributeNames.CUSTOM_GROUP_KEYS).value;
    let text = this._attributeSrv.attributes.get(ConfigAttributeNames.CUSTOM_GROUP_KEYS).options.tooltipText;

    fieldOptions.key?.split('/').reverse().forEach((key) => {
      attributeControl = attributeControl.get(key);
      disabled = disabled[key];
    });

    if (disabled) {
      attributeControl.disable();
      this.tooltipText = text;
    } else {
      attributeControl.enable();
      this.tooltipText = this.wrapperOptions.tooltipText;
    }

    return attributeControl as FormControl;
  }
}
