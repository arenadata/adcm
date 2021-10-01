import { Injectable } from '@angular/core';
import { IConfigAttr } from '../types';
import { GroupKeysWrapperComponent } from '@app/shared/configuration/attribute-provider/attributes/group-keys/group-keys-wrapper.component';

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

  readonly attributes: Attributes;

  constructor(json: IConfigAttr) {
    this.attributes = this._buildAttributes(json);
  }

  getByName(name: ConfigAttributeNames): ConfigAttribute {
    return this.attributes.has(name) ? this.attributes.get(name) : undefined;
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
      meta: {
        wrapper: GroupKeysWrapperComponent,
        tooltipText: 'ConfigAttributeNames.CUSTOM_GROUP_KEYS tooltip text'
      }
    };
  }

  private [ConfigAttributeNames.CUSTOM_GROUP_KEYS](value: ConfigAttributeValue): ConfigAttribute {
    return {
      name: ConfigAttributeNames.CUSTOM_GROUP_KEYS,
      value
    };
  }
}
