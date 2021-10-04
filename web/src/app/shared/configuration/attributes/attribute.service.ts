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
}

export enum ConfigAttributeNames {
  GROUP_KEYS = 'group_keys',
  CUSTOM_GROUP_KEYS = 'custom_group_keys'
}

export interface ConfigAttributesJSON {
  [key: string]: any;
}

export interface ConfigAttributeOptions {
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
      new ConfigAttributeFactory().create(attr, json[attr], configs[attr], this._createFormForAttribute(json, attr)),
    ]));
  }

  private _createFormForAttribute(json: ConfigAttributesJSON, attr: ConfigAttributeNames): FormGroup {
    const buildFormGroup = (json: boolean | ConfigAttributesJSON) => {
      const data = Object.entries(json).map(([key, value]) => [key, value]).reduce((acc, [key, value]: [string, boolean | ConfigAttributesJSON]) => {

        if (isBoolean(value) || isEmptyObject(value)) {
          return { ...acc, [key]: value };
        } else if (!isEmptyObject(value)) {
          return { ...acc, [key]: buildFormGroup(value) };
        }

      }, {});

      return this._fb.group(data);
    };

    return buildFormGroup(json[attr]);
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

export class ConfigAttributeFactory {

  create(name: ConfigAttributeNames, value: ConfigAttributesJSON, options: AttributeOptions, form: FormGroup): ConfigAttribute {
    if (!this[name]) {
      return;
    }

    return this[name](value, options, form);
  }

  [ConfigAttributeNames.GROUP_KEYS](value: ConfigAttributesJSON, {
    name,
    options,
    wrapper
  }: AttributeOptions, form: FormGroup): ConfigAttribute {
    return { name, value, wrapper, options, form };
  }

  [ConfigAttributeNames.CUSTOM_GROUP_KEYS](value: ConfigAttributesJSON, { name }: AttributeOptions, form: FormGroup): ConfigAttribute {
    return { name, value, form };
  }

}
