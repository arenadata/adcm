import { Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { concatMap, filter, map, switchMap, take } from 'rxjs/operators';
import { Observable } from 'rxjs';
import { AdcmEntity, AdcmTypedEntity } from '@app/models/entity';
import { TypeName } from '@app/core/types';
import { Action, Store } from '@ngrx/store';

import { ApiService } from '@app/core/api';
import { ServiceComponentService } from '@app/services/service-component.service';
import { ClusterService } from '@app/core/services/cluster.service';
import { EntityNames } from '@app/models/entity-names';
import {
  getEventEntityType,
  getNavigationPath,
  getPath,
  setPath,
  setPathOfRoute
} from '@app/store/navigation/navigation.store';
import { EventMessage, socketResponse } from '@app/core/store/sockets/socket.reducer';
import { IClusterService } from '@app/models/cluster-service';
import { ConfigGroupListService } from '@app/config-groups/service/config-group-list.service';
import { ConcernEventType } from '@app/models/concern/concern-reason';

@Injectable()
export class NavigationEffects {

  setPathOfRoute$ = createEffect(
    () =>
      this.actions$.pipe(
        ofType(setPathOfRoute),
        filter(action => !!action.params),
        switchMap(action => {
          const getters: Observable<AdcmTypedEntity>[] = action.params.keys?.reduce((acc, param) => {
            const getter = this.entityGetter(param as TypeName, +action.params.get(param));
            if (getter) {
              acc.push(getter);
            }

            return acc;
          }, []);
          return getPath(getters);
        }),
      ),
  );

  changePathOfEvent$ = createEffect(() => this.actions$.pipe(
    ofType(socketResponse),
    filter(action =>
      [ConcernEventType.Service, ConcernEventType.Cluster, ConcernEventType.Host, ConcernEventType.HostProvider, ConcernEventType.ServiceComponent].includes(action.message.object.type as any)
    ),
    concatMap((event: { message: EventMessage }) => {
      return new Observable<Action>(subscriber => {
        this.store.select(getNavigationPath).pipe(take(1)).subscribe((path) => {
          if (path?.some(item => item.typeName === getEventEntityType(event.message.object.type) && event.message.object.id === item.id)) {
            this.entityGetter(getEventEntityType(event.message.object.type), event.message.object.id)
              .subscribe((entity) => {
                subscriber.next(setPath({
                  path: path.reduce((acc, item) =>
                    acc.concat(getEventEntityType(event.message.object.type) === item.typeName && item.id === event.message.object.id ? entity : item), []),
                }));
                subscriber.complete();
              }, () => subscriber.complete());
          } else {
            subscriber.complete();
          }
        }, () => subscriber.complete());
      });
    }),
  ));

  constructor(
    private actions$: Actions,
    private api: ApiService,
    private serviceComponentService: ServiceComponentService,
    private store: Store,
    private clusterService: ClusterService,
    private configGroupService: ConfigGroupListService
  ) {}

  entityGetter(type: TypeName, id: number): Observable<AdcmTypedEntity> {
    const entityToTypedEntity = (getter: Observable<AdcmEntity>, typeName: TypeName) => getter.pipe(
      map(entity => ({
        ...entity,
        typeName,
      } as AdcmTypedEntity))
    );

    if (EntityNames.includes(type)) {
      if (type === 'bundle') {
        return entityToTypedEntity(
          this.clusterService.one_bundle(id),
          type,
        );
      } else if (type === 'servicecomponent' || type === 'component') {
        return entityToTypedEntity(
          this.serviceComponentService.get(id),
          type,
        );
      }
      if (type === 'service') {
        return entityToTypedEntity(
          this.api.getOne<any>(type, id),
          type,
        ).pipe(switchMap((entity) => {
          return this.api.getOne<any>('cluster', (entity as any as IClusterService).cluster_id)
            .pipe(map(cluster => ({ ...entity, cluster })));
        }));
      } else if (type === 'group_config') {
        return entityToTypedEntity(
          this.configGroupService.get(id),
          type,
        );
      } else {
        return entityToTypedEntity(
          this.api.getOne<any>(type, id),
          type,
        );
      }
    }
  }

}
