import { Inject, Injectable, InjectionToken, TemplateRef, Type } from '@angular/core';
import { FormBuilder, FormGroup } from '@angular/forms';
import { IFieldOptions } from '@app/shared/configuration/types';
import { isBoolean, isEmptyObject } from '@app/core/types';

export const ATTRIBUTES_OPTIONS = new InjectionToken('Attributes options');

export interface AttributeOptions {
  name: ConfigAttributeNames;
  wrapper?: Type<AttributeWrapper>;
  options?: ConfigAttributeOptions;
}

export type AttributesOptions = Record<ConfigAttributeNames, AttributeOptions>

export interface AttributeWrapper {
  fieldTemplate: TemplateRef<any>;
  wrapperOptions: ConfigAttributeOptions;
  fieldOptions: IFieldOptions;
  attributeForm: FormGroup;
  parametersForm: FormGroup;
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

  get attributes(): Attributes {
    return this._attributes;
  }

  private _attributes: Attributes;

  constructor(@Inject(ATTRIBUTES_OPTIONS) private _configs: AttributesOptions, private _fb: FormBuilder) {
  }

  init(json: ConfigAttributesJSON): void {
    this._attributes = this._createAttributes(this._activeAttributes, json, this._configs);
  }

  getByName(name: ConfigAttributeNames): ConfigAttribute {
    return this._attributes.has(name) ? this._attributes.get(name) : undefined;
  }

  private _createAttributes(_activeAttributes: Partial<ConfigAttributeNames>[], json: ConfigAttributesJSON, configs: AttributesOptions): Attributes {
    if (!Object.keys(json || {}).length) {
      return;
    }

    return new Map(this._activeAttributes.map((attr) => [
      attr,
      new ConfigAttributeFactory(this._fb).create(attr, json[attr], configs[attr], json),
    ]));
  }


  rawAttributes() {
    let json = {};
    if (this._attributes) {
      for (const [key, value] of this._attributes.entries()) {
        json = {
          ...json,
          [key]: value.form.value
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
        return { ...acc, [key]: buildFormGroup(value) };
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
