import { ApiFlat, IConfigGroup } from '../core/types';

export class ConfigGroup extends ApiFlat implements IConfigGroup {
  public name: string;
  public description: string;
  public hosts: unknown[] = [];
  public config: string;

  action = '';
  display_name = '';
  typeName = '';

  constructor(options: IConfigGroup) {
    super(options.id, options.object_id, options.object_type, options.url);
    this.name = options.name;
    this.description = options.description ?? '';
    this.hosts = options.hosts ?? [];
    this.config = options.config;
  }


}
