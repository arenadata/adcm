import { Pipe, PipeTransform } from '@angular/core';

import { AdcmTypedEntity } from '@app/models/entity';
import { IStyledNavItem } from '@app/shared/details/navigation.service';
import { TypeName } from '@app/core/types';

@Pipe({
  name: 'navItem'
})
export class NavItemPipe implements PipeTransform {

  getGroupName(typeName: TypeName): string {
    switch (typeName) {
      case 'cluster':
        return 'clusters';
      case 'service':
        return 'services';
      case 'servicecomponent':
        return 'components';
      case 'host':
        return 'hosts';
    }
  }

  getLink(path: AdcmTypedEntity[], index: number, group: boolean): string {
    switch (path[index].typeName) {
      case 'cluster':
        return group ? `/${path[index].typeName}` : `/${path[index].typeName}/${path[index].id}`;
      case 'service':
        return group ? (
          `/${path[index - 1].typeName}/${path[index - 1].id}/service`
        ) : (
          `/${path[index - 1].typeName}/${path[index - 1].id}/service/${path[index].id}`
        );
      case 'servicecomponent':
        return group ? (
          `/${path[index - 2].typeName}/${path[index - 2].id}/service/${path[index - 1].id}/component`
        ) : (
          `/${path[index - 2].typeName}/${path[index - 2].id}/service/${path[index - 1].id}/component/${path[index].id}`
        );
      case 'host':
        return group ? (
          `/${path[index - 1].typeName}/${path[index - 1].id}/host`
        ) : (
          `/${path[index - 1].typeName}/${path[index - 1].id}/host/${path[index].id}`
        );
    }
  }

  getEntityTitle(entity: AdcmTypedEntity): string {
    return entity.typeName === 'host' ? entity.fqdn : entity.display_name || entity.name;
  }

  transform(path: AdcmTypedEntity[]): IStyledNavItem[] {
    return path?.reduce((acc, item, index) => {
      return [
        ...acc,
        {
          title: this.getGroupName(item.typeName),
          url: this.getLink(path, index, true),
          class: 'type-name',
        },
        {
          title: this.getEntityTitle(item),
          url: this.getLink(path, index, false),
          class: 'entity',
          entity: item,
        }
      ] as IStyledNavItem[];
    }, []);
  }

}
