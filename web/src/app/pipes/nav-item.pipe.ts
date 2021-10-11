import { Pipe, PipeTransform } from '@angular/core';

import { AdcmTypedEntity } from '@app/models/entity';
import { IStyledNavItem } from '@app/shared/details/navigation.service';
import { ApiFlat, TypeName } from '@app/core/types';

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
      case 'component':
        return 'components';
      case 'host':
        return 'hosts';
      case 'provider':
        return 'hostproviders';
      case 'group_config':
        return 'groupconfigs';
    }
  }

  getLink(path: AdcmTypedEntity[], index: number, group: boolean): string {
    let cluster: AdcmTypedEntity;

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
      case 'component':
        return group ? (
          `/${path[index - 2].typeName}/${path[index - 2].id}/service/${path[index - 1].id}/component`
        ) : (
          `/${path[index - 2].typeName}/${path[index - 2].id}/service/${path[index - 1].id}/component/${path[index].id}`
        );
      case 'host':
        cluster = path.find(item => item.typeName === 'cluster');
        if (cluster) {
          return group ? (
            `/${cluster.typeName}/${cluster.id}/host`
          ) : (
            `/${cluster.typeName}/${cluster.id}/host/${path[index].id}`
          );

        }
        return group ? `/${path[index].typeName}` : `/${path[index].typeName}/${path[index].id}`;
      case 'provider':
        return group ? `/${path[index].typeName}` : `/${path[index].typeName}/${path[index].id}`;
      case 'group_config':
        cluster = path[0];
        const { object_type, object_id, id } = (path[index] as unknown as ApiFlat);
        if (object_type === 'service') {
          return group ? (
            `/${cluster.typeName}/${cluster.id}/${object_type}/${object_id}/group_config`
          ) : (
            `/${cluster.typeName}/${cluster.id}/${object_type}/${object_id}/group_config/${id}`
          );
        } else if (object_type === 'component') {
          return group ? (
            `/${path[index - 3].typeName}/${path[index - 3].id}/service/${path[index - 2].id}/component/${path[index-1].id}/group_config`
          ) : (
            `/${path[index - 3].typeName}/${path[index - 3].id}/service/${path[index - 2].id}/component/${path[index-1].id}/group_config/${id}`
          );
        }
      {
        return group ? (
          `/${object_type}/${object_id}/group_config`
        ) : (
          `/${object_type}/${object_id}/group_config/${id}`
        );
      }

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
