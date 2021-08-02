import { IConfigGroup, TypeName } from '../core/types';

export class ConfigGroup implements IConfigGroup {
  public id: number;
  public object_id: number;
  public object_type: TypeName;
  public url: string;

  public name: string;
  public description: string;
  public hosts: unknown[] = [];
  public config: string;

  typeName: TypeName = 'config_group';

  constructor(options) {
    this.name = options.name;
    this.description = options.description ?? '';
    this.hosts = options.hosts ?? [];
    this.config = options.config;
    this.id = options.id;
    this.object_id = options.object_id;
    this.object_type = options.object_type;
    this.url = options.url;
  }
}
