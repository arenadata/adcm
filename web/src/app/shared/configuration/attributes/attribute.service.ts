import { Inject, Injectable, InjectionToken, TemplateRef, Type } from '@angular/core';
import { FormBuilder, FormGroup } from '@angular/forms';
import { IFieldOptions } from '@app/shared/configuration/types';
import { isBoolean, isEmptyObject } from '@app/core/types';
import { FieldComponent } from '@app/shared/configuration/field/field.component';

export const ATTRIBUTES_OPTIONS = new InjectionToken('Attributes options');

export interface AttributeOptions {
  name: ConfigAttributeNames;
  wrapper?: Type<AttributeWrapper>;
  options?: ConfigAttributeOptions;
}

export type AttributesOptions = Record<ConfigAttributeNames, AttributeOptions>

export interface AttributeWrapper {
  uniqId: string;
  fieldTemplate: TemplateRef<any>;
  wrapperOptions: ConfigAttributeOptions;
  fieldOptions: IFieldOptions;
  attributeForm: FormGroup;
  parametersForm: FormGroup;
  field: FieldComponent;
}

export enum ConfigAttributeNames {
  // an attribute for adding config parameters to group
  GROUP_KEYS = 'group_keys',
  // an attribute for config parameters that determines whether this parameter can be added to the config group
  CUSTOM_GROUP_KEYS = 'custom_group_keys'
}

export interface ConfigAttributesJSON {
  [key: string]: any;
}

export interface ConfigAttributeOptions {
  tooltipText?: string;

  [key: string]: any;
}

export type ConfigAttribute = AttributeOptions & { value: ConfigAttributesJSON, form: FormGroup };

export type Attributes = Map<ConfigAttributeNames, ConfigAttribute>;

@Injectable()
export class AttributeService {

  private readonly _activeAttributes: Partial<ConfigAttributeNames>[] = [
    ConfigAttributeNames.GROUP_KEYS,
    ConfigAttributeNames.CUSTOM_GROUP_KEYS
  ];

  get attributes(): Attributes[] {
    return this._attributes;
  }

  private _attributes: Attributes[] = [];

  constructor(@Inject(ATTRIBUTES_OPTIONS) private _configs: AttributesOptions, private _fb: FormBuilder) {
  }

  init(json: ConfigAttributesJSON): string {
    const uniqId = Math.random().toString(36).slice(2);
    this._attributes[uniqId] = this._createAttributes(this._activeAttributes, json, this._configs);

    return uniqId;
  }

  getByName(name: ConfigAttributeNames, uniqId): ConfigAttribute {
    return this._attributes[uniqId].has(name) ? this._attributes[uniqId].get(name) : undefined;
  }

  groupCheckboxToggle(groupName, value, uniqId): void {
    this.attributes[uniqId].get(ConfigAttributeNames.GROUP_KEYS).value[groupName].value = value
  }

  private _createAttributes(_activeAttributes: Partial<ConfigAttributeNames>[], json: ConfigAttributesJSON, configs: AttributesOptions): Attributes {
    const isEmptyAttrs = !Object.keys(json || {}).length;
    const isActiveAttrsPresent = !!Object.keys(json || {}).filter((x: ConfigAttributeNames) => this._activeAttributes.includes(x)).length;
    if (isEmptyAttrs || !isActiveAttrsPresent) {
      return;
    }

    return new Map(this._activeAttributes.map((attr) => [
      attr,
      new ConfigAttributeFactory(this._fb).create(attr, json[attr], configs[attr], json),
    ]));
  }

  removeAttributes(uniqId) {
    delete this._attributes[uniqId];
  }

  rawAttributes(uniqId) {
    let json = {};
    if (this._attributes[uniqId]) {
      for (const [key, value] of this._attributes[uniqId].entries()) {
        json = {
          ...json,
          [key]: value.form.getRawValue()
        };
      }
    }

    return json;
  }
}

export const createFormForAttribute = (fb: FormBuilder, json: ConfigAttributesJSON, attr: ConfigAttributeNames, disabled: boolean = false): FormGroup => {
  const buildFormGroup = (json: boolean | ConfigAttributesJSON) => {
    const data = Object.entries(json).map(([key, value]) => [key, value]).reduce((acc, [key, value]: [string, boolean | ConfigAttributesJSON]) => {

      if (isBoolean(value) || isEmptyObject(value)) {
        return {
          ...acc,
          [key]: { value, disabled }
        };
      } else if (!isEmptyObject(value)) {
        return { ...acc, [key]: buildFormGroup(value['fields']) };
      }

    }, {});

    return fb.group(data);
  };

  return buildFormGroup(json[attr]);
};


export class ConfigAttributeFactory {

  constructor(private fb: FormBuilder) {}

  create(name: ConfigAttributeNames, value: ConfigAttributesJSON, options: AttributeOptions, json: ConfigAttributesJSON): ConfigAttribute {
    if (!this[name]) {
      return;
    }

    return this[name](value, options, json);
  }

  [ConfigAttributeNames.GROUP_KEYS](value: ConfigAttributesJSON, {
    name,
    options,
    wrapper
  }: AttributeOptions, json: ConfigAttributesJSON): ConfigAttribute {

    const form = createFormForAttribute(this.fb, json, name);

    return {
      name,
      value,
      wrapper,
      options,
      form
    };
  }

  [ConfigAttributeNames.CUSTOM_GROUP_KEYS](value: ConfigAttributesJSON, {
    name,
    options
  }: AttributeOptions, json: ConfigAttributesJSON): ConfigAttribute {

    const form = createFormForAttribute(this.fb, json, name);

    return { name, value, options, form };
  }

}
