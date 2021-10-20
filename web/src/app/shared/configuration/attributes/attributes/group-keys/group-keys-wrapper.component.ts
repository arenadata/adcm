import { Component, Input, OnInit, TemplateRef } from '@angular/core';
import {
  AttributeService,
  AttributeWrapper,
  ConfigAttributeNames,
  ConfigAttributeOptions
} from '@app/shared/configuration/attributes/attribute.service';
import { AbstractControl, FormControl, FormGroup } from '@angular/forms';
import { IFieldOptions } from '@app/shared/configuration/types';
import { BaseDirective } from '@adwp-ui/widgets';
import { MatCheckboxChange } from '@angular/material/checkbox';

@Component({
  selector: 'app-group-keys-wrapper',
  template: `
    <div class="group-keys-wrapper">
      <div class="group-checkbox">
        <mat-checkbox [matTooltip]="tooltipText" [formControl]="groupControl"
                      (change)="onChange($event)"></mat-checkbox>
      </div>
      <div class="group-field">
        <ng-container *ngTemplateOutlet="fieldTemplate"></ng-container>
      </div>
    </div>
  `,
  styleUrls: ['group-keys-wrapper.component.scss'],
})
export class GroupKeysWrapperComponent extends BaseDirective implements AttributeWrapper, OnInit {
  tooltipText: string = '';

  groupControl: FormControl;

  parameterControl: FormControl;

  @Input() fieldTemplate: TemplateRef<any>;

  @Input() wrapperOptions: ConfigAttributeOptions;

  @Input() attributeForm: FormGroup;

  @Input() parametersForm: FormGroup;

  @Input() fieldOptions: IFieldOptions;

  constructor(private _attributeSrv: AttributeService) {
    super();
  }


  ngOnInit(): void {
    this._resolveAndSetupControls(this.attributeForm, this.parametersForm, this.fieldOptions);
  }

  private _resolveAndSetupControls(attributeForm: FormGroup, parametersForm: FormGroup, fieldOptions: IFieldOptions): void {
    let attributeControl: AbstractControl = attributeForm;
    let parameterControl: AbstractControl = parametersForm;
    let disabled = this._attributeSrv.attributes.get(ConfigAttributeNames.CUSTOM_GROUP_KEYS).value;
    let text = this._attributeSrv.attributes.get(ConfigAttributeNames.CUSTOM_GROUP_KEYS).options.tooltipText;

    fieldOptions.key?.split('/').reverse().forEach((key) => {
      attributeControl = attributeControl.get(key);
      parameterControl = parameterControl.get(key);
      disabled = disabled[key];
    });

    this.groupControl = attributeControl as FormControl;
    this.parameterControl = parameterControl as FormControl;

    if (!disabled) {
      attributeControl.disable();
      parameterControl.disable();

      this.tooltipText = text;
    } else {
      attributeControl.enable();
      if (attributeControl.value) {
        parameterControl.enable();
      } else {
        parameterControl.disable();
      }

      this.tooltipText = this.wrapperOptions.tooltipText;
    }

  }

  onChange(e: MatCheckboxChange) {
    if (e.checked) {
      this.parameterControl.enable();
    } else {
      this.parameterControl.disable();
    }
  }
}
