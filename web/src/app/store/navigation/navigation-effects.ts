import { Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { concatMap, filter, map, switchMap, take } from 'rxjs/operators';
import { Observable } from 'rxjs';
import { Action, Store } from '@ngrx/store';

import { AdcmTypedEntity } from '@app/models/entity';
import { TypeName } from '@app/core/types';
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
import { EntityHelper } from '@app/helpers/entity-helper';

@Injectable()
export class NavigationEffects {

  setPathOfRoute$ = createEffect(
    () =>
      this.actions$.pipe(
        ofType(setPathOfRoute),
        filter(action => !!action.params),
        switchMap(action => {
          const getters: Observable<AdcmTypedEntity>[] = action.params.keys.reduce((acc, param) => {
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
    filter(action => ['raise_issue', 'clear_issue'].includes(action.message.event)),
    concatMap((event: { message: EventMessage }) => {
      return new Observable<Action>(subscriber => {
        this.store.select(getNavigationPath).pipe(take(1)).subscribe((path) => {
          if (path.some(item => item.typeName === getEventEntityType(event.message.object.type) && event.message.object.id === item.id)) {
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
    private clusterService: ClusterService
  ) {}

  entityGetter(type: TypeName, id: number): Observable<AdcmTypedEntity> {
    if (EntityNames.includes(type)) {
      if (type === 'bundle') {
        return EntityHelper.entityToTypedEntity(
          this.clusterService.one_bundle(id),
          type,
        );
      } else if (type === 'servicecomponent') {
        return EntityHelper.entityToTypedEntity(
          this.serviceComponentService.get(id),
          type,
        );
      } if (type === 'service') {
        return EntityHelper.entityToTypedEntity(
          this.api.getOne<any>(type, id),
          type,
        ).pipe(switchMap((entity) => {
          return this.api.getOne<any>('cluster', (entity as any as IClusterService).cluster_id)
            .pipe(map(cluster => ({...entity, cluster})));
        }));
      } else {
        return EntityHelper.entityToTypedEntity(
          this.api.getOne<any>(type, id),
          type,
        );
      }
    }
  }

}
