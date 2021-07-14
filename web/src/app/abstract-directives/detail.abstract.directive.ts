import { Directive, OnDestroy, OnInit } from '@angular/core';
import { switchMap, tap } from 'rxjs/operators';
import { Observable, Subscription } from 'rxjs';
import { Store } from '@ngrx/store';
import { ActivatedRoute } from '@angular/router';

import { SocketListenerDirective } from './socketListener.directive';
import { ClusterService, WorkerInstance } from '@app/core/services/cluster.service';
import { Cluster, Host, IAction, Issue, Job, isIssue } from '@app/core/types';
import { IDetails } from '@app/shared/details/navigation.service';
import { AdcmEntity } from '@app/models/entity';
import { getNavigationPath } from '@app/store/navigation/navigation.store';
import { EventMessage, SocketState } from '@app/core/store';
import { ChannelService, keyChannelStrim } from '@app/core/services';

@Directive({
  selector: '[appDetailAbstract]',
})
export abstract class DetailAbstractDirective extends SocketListenerDirective implements OnInit, OnDestroy {

  request$: Observable<WorkerInstance>;
  subscription$: Subscription;
  upgradable = false;
  actions: IAction[] = [];
  status: number | string;
  issue: Issue;
  current: IDetails;
  currentName = '';

  navigationPath: Observable<AdcmEntity[]> = this.store.select(getNavigationPath).pipe(this.takeUntil());

  constructor(
    protected socket: Store<SocketState>,
    protected route: ActivatedRoute,
    protected service: ClusterService,
    protected channel: ChannelService,
    protected store: Store,
  ) {
    super(socket);
  }

  get Current() {
    return this.service.Current;
  }

  ngOnInit(): void {
    console.log('init');
    this.request$ = this.route.paramMap.pipe(
      this.takeUntil(),
      switchMap((param) => {
        console.log('param', param);
        return this.service.getContext(param);
      }),
      tap((w) => this.run(w))
    );
    this.subscription$ = this.request$.subscribe();

    super.startListenSocket();
  }

  ngOnDestroy(): void {
    this.service.clearWorker();
  }

  get isIssue() {
    return isIssue(this.issue);
  }

  run(w: WorkerInstance) {
    const {
      id,
      name,
      typeName,
      action,
      actions,
      issue,
      status,
      prototype_name,
      prototype_display_name,
      prototype_version,
      bundle_id,
      state,
    } = w.current;
    const { upgradable, upgrade, hostcomponent } = w.current as Cluster;
    const { log_files, objects } = w.current as Job;
    const { provider_id } = w.current as Host;

    this.currentName = name;
    this.actions = actions;
    this.upgradable = upgradable;
    this.status = status;

    const parent = w.current.typeName === 'cluster' ? null : w.cluster;
    this.issue = issue;

    this.current = {
      parent,
      id,
      name,
      typeName,
      actions,
      action,
      issue,
      upgradable,
      upgrade,
      status,
      state,
      log_files,
      objects,
      prototype_name,
      prototype_display_name,
      prototype_version,
      provider_id,
      bundle_id,
      hostcomponent,
    };
  }

  scroll(stop: { direct: -1 | 1 | 0; screenTop: number }) {
    this.channel.next(keyChannelStrim.scroll, stop);
  }

  reset() {
    if (this.subscription$) {
      this.subscription$.unsubscribe();
    }
    this.request$ = this.service.reset().pipe(
      this.takeUntil(),
      tap((a) => this.run(a))
    );
    this.subscription$ = this.request$.subscribe();
  }

  socketListener(m: EventMessage) {
    if ((m.event === 'create' || m.event === 'delete') && m.object.type === 'bundle') {
      this.reset();
      return;
    }

    const type = m.object.type === 'component' ? 'servicecomponent' : m.object.type;
    if (this.Current?.typeName === type && this.Current?.id === m.object.id) {
      if (this.service.Current.typeName === 'job' && (m.event === 'change_job_status' || m.event === 'add_job_log')) {
        this.reset();
        return;
      }

      if (m.event === 'change_state' || m.event === 'upgrade') {
        this.reset();
        return;
      }
      if (m.event === 'clear_issue') this.issue = {};
      if (m.event === 'raise_issue') this.issue = m.object.details.value;
      if (m.event === 'change_status') this.status = +m.object.details.value;
    }

    // parent
    if (this.service.Cluster?.id === m.object.id && this.Current?.typeName !== 'cluster' && type === 'cluster' && m.event === 'clear_issue') this.issue = {};
  }

}
