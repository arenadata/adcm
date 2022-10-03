import { Component, Input, OnInit, TemplateRef } from '@angular/core';
import {
  AttributeService,
  AttributeWrapper,
  ConfigAttributeNames,
  ConfigAttributeOptions
} from '@app/shared/configuration/attributes/attribute.service';
import { FormControl, FormGroup } from '@angular/forms';
import { IFieldOptions } from '@app/shared/configuration/types';
import { BaseDirective } from '@adwp-ui/widgets';
import { MatCheckboxChange } from '@angular/material/checkbox';
import { FieldComponent } from '@app/shared/configuration/field/field.component';

@Component({
  selector: 'app-group-keys-wrapper',
  template: `
    <div class="group-keys-wrapper">
      <div class="group-checkbox">
        <mat-checkbox
          [matTooltip]="tooltipText"
          [formControl]="groupControl"
          (change)="onChange($event)"
        ></mat-checkbox>
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

  parameterControl: () => FormControl;

  @Input() uniqId: string;

  @Input() fieldTemplate: TemplateRef<any>;

  @Input() wrapperOptions: ConfigAttributeOptions;

  @Input() attributeForm: FormGroup;

  @Input() parametersForm: FormGroup;

  @Input() fieldOptions: IFieldOptions;

  @Input() field: FieldComponent;

  private _disabled: boolean;

  constructor(private _attributeSrv: AttributeService) {
    super();
  }

  ngOnInit(): void {
    this._resolveAndSetupControls(this.attributeForm, this.parametersForm, this.fieldOptions);
    Promise.resolve().then(() => {
      this._restoreStatus();
      this.disableIfReadOnly();
    });
  }

  repairControlsAfterSave(currentParametersForm) {
    this._resolveAndSetupControls(this.attributeForm, currentParametersForm, this.fieldOptions);
  }

  private disableIfReadOnly() {
    if (this.field?.options?.read_only) {
      this.groupControl.disable();
    }
  }

  private _resolveAndSetupControls(attributeForm: FormGroup, parametersForm: FormGroup, fieldOptions: IFieldOptions): void {
    let attributeControl: FormGroup = attributeForm;
    let parameterControl: FormGroup = parametersForm;
    let enabled = this._attributeSrv.attributes[this.uniqId].get(ConfigAttributeNames.CUSTOM_GROUP_KEYS).value;
    let text = this._attributeSrv.attributes[this.uniqId].get(ConfigAttributeNames.CUSTOM_GROUP_KEYS).options.tooltipText;

    const path = fieldOptions.key?.split('/').reverse();

    this.groupControl = attributeControl.get(path) as FormControl;
    this.parameterControl = () => parameterControl.get(path) as FormControl;

    if (!this.groupControl || !this.parameterControl()) return;

    path.forEach((part) => {
      enabled = this._getFieldValue(enabled, part);
    });

    if (!enabled) {
      Promise.resolve().then(() => {
        this.groupControl.disable();
        this.parameterControl().disable();

        this.tooltipText = text;
      });
    } else {
      Promise.resolve().then(() => {
        this.groupControl.enable();
        if (this.groupControl.value) {
          this.parameterControl().enable();
        } else {
          this.parameterControl().disable();
        }
        this.disableIfReadOnly();
      })

      this.tooltipText = this.wrapperOptions.tooltipText;
      this._disabled = !attributeControl.value;
    }
  }

  onChange(e: MatCheckboxChange) {
    if (e.checked) {
      this.parameterControl().enable();
      this.field.disabled = false;
    } else {
      this.parameterControl().disable();
      this.field.disabled = true;
    }
  }

  private _restoreStatus() {
    if (this.field?.disabled) {
      this.field.disabled = this._disabled;
    }
  }

  private _getFieldValue(attr, key) {
    if (attr?.fields) return attr?.fields[key]

    return attr[key];
  }
}
