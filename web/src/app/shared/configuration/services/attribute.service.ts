import { Injectable } from '@angular/core';
import { IConfigAttr } from '@app/shared/configuration/types';

export enum ConfigAttributeNames {
  CUSTOM_GROUP_KEYS = 'custom_group_keys',
  GROUP_KEYS = 'group_keys',
}

export interface ConfigAttributeValue {
  [key: string]: boolean;
}

export interface ConfigAttributeMeta {
  [key: string]: any;
}

export interface ConfigAttribute {
  name: ConfigAttributeNames,
  value: ConfigAttributeValue;
  meta?: ConfigAttributeMeta;
}

export type Attributes = Map<ConfigAttributeNames, ConfigAttribute>;

@Injectable()
export class AttributeService {

  private readonly _activeAttributes: ConfigAttributeNames[] = [
    ConfigAttributeNames.CUSTOM_GROUP_KEYS,
    ConfigAttributeNames.GROUP_KEYS
  ];

  readonly _attributes: Attributes;

  constructor(json: IConfigAttr) {
    this._attributes = this._buildAttributes(json);
  }

  getByName(name: ConfigAttributeNames): ConfigAttribute {
    return this._attributes.has(name) ? this._attributes.get(name) : undefined;
  }

  private _buildAttributes(json: IConfigAttr): Attributes {
    if (!json) {
      return;
    }

    return new Map(this._activeAttributes.map((attr) => [
      attr,
      new ConfigAttributeFactory().create(attr, json[attr]),
    ]));
  }
}

export class ConfigAttributeFactory {

  create(name: ConfigAttributeNames, value: ConfigAttributeValue): ConfigAttribute {
    if (!this[name]) {
      return;
    }

    return this[name](value);
  }

  private [ConfigAttributeNames.GROUP_KEYS](value: ConfigAttributeValue): ConfigAttribute {
    return {
      name: ConfigAttributeNames.GROUP_KEYS,
      value,
    };
  }

  private [ConfigAttributeNames.CUSTOM_GROUP_KEYS](value: ConfigAttributeValue): ConfigAttribute {
    return {
      name: ConfigAttributeNames.CUSTOM_GROUP_KEYS,
      value,
      meta: {
        tooltipText: 'ConfigAttributeNames.CUSTOM_GROUP_KEYS tooltip text'
      }
    };
  }
}
