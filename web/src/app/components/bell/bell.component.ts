import { AfterViewInit, Component, ElementRef, OnInit, Renderer2, ViewChild } from '@angular/core';
import { JobService } from '@app/services/job.service';
import { BaseDirective } from '@adwp-ui/widgets';
import { TaskService } from '@app/services/task.service';
import { BehaviorSubject, combineLatest, interval, Observable, zip } from 'rxjs';
import { filter, map, take, takeWhile } from 'rxjs/operators';
import { ACKNOWLEDGE_EVENT, NotificationsComponent } from '@app/components/notifications/notifications.component';
import { Task, TaskRaw } from '@app/core/types';
import { EventMessage } from '@app/core/store';

const RUNNING_COLOR = '#FFEA00';
const SUCCESS_COLOR = '#1EE564';
const FAILED_COLOR = '#FF8A80';

export interface NotificationsData {
  runningCount: number;
  successCount: number;
  failedCount: number;
}

@Component({
  selector: 'app-bell',
  template: `
    <div
      class="circle"
      [ngStyle]="{ background: bellGradient }"
      routerLink="/task"
      appPopover
      [component]="NotificationsComponent"
      [event]="bindedPopoverEvent"
      [data]="{ counts: counts, tasks: tasks }"
    >
      <div class="animation hide" (animationstart)="onAnimationStart()" (animationend)="onAnimationEnd()" #animation></div>
      <div class="insider">
        <mat-icon>notifications</mat-icon>
      </div>
    </div>
  `,
  styleUrls: ['./bell.component.scss']
})
export class BellComponent extends BaseDirective implements AfterViewInit {

  NotificationsComponent = NotificationsComponent;

  @ViewChild('animation', { static: false }) animationRef: any;

  runningCount = new BehaviorSubject<number>(0);
  successCount = new BehaviorSubject<number>(0);
  failedCount = new BehaviorSubject<number>(0);

  bellGradient = '';

  isAnimationRunning = new BehaviorSubject<boolean>(false);
  animationElem = new BehaviorSubject<Element>(null);

  counts = new BehaviorSubject<NotificationsData>(null);
  tasks = new BehaviorSubject<TaskRaw[]>([]);

  readonly bindedPopoverEvent = this.popoverEvent.bind(this);

  constructor(
    private jobService: JobService,
    private taskService: TaskService,
    private renderer: Renderer2,
  ) {
    super();
  }

  popoverEvent(event: any) {
    if (event === ACKNOWLEDGE_EVENT) {
      this.tasks.next([]);
    }
  }

  onAnimationStart() {
    this.isAnimationRunning.next(true);
  }

  onAnimationEnd() {
    this.isAnimationRunning.next(false);
  }

  startAnimation() {
    if (this.animationElem.value && !this.isAnimationRunning.value) {
      this.renderer.removeClass(this.animationElem.value, 'hide');
      this.renderer.addClass(this.animationElem.value, 'animated');
    }
  }

  endAnimation() {
    if (this.animationElem.value) {
      this.renderer.addClass(this.animationElem.value, 'hide');
      this.renderer.removeClass(this.animationElem.value, 'animated');
    }
  }

  afterCountChanged() {
    // console.log('changed', this.runningCount, this.successCount, this.failedCount);
    const total =  this.runningCount.value + this.successCount.value + this.failedCount.value;
    if (total > 0) {
      const degOne = 360 / total;
      const degRunning = this.runningCount.value * degOne;
      const degSuccess = this.successCount.value * degOne;
      // const degFailed = this.failedCount.value * degOne;
      this.bellGradient =
        `conic-gradient(`
        + `${RUNNING_COLOR} 0deg ${degRunning}deg,`
        + `${SUCCESS_COLOR} ${degRunning}deg ${degRunning + degSuccess}deg,`
        + `${FAILED_COLOR} ${degRunning + degSuccess}deg 360deg)`;
    } else {
      this.bellGradient = 'transparent';
    }
    this.startAnimation();
  }

  getChangeJobObservable(): Observable<EventMessage> {
    return this.jobService.events(['change_job_status']).pipe(this.takeUntil());
  }

  listenToJobs() {
    this.getChangeJobObservable().subscribe((event) => {
      const status = event.object.details.value;
      if (status === 'running') {
        this.runningCount.next(this.runningCount.value + 1);
        this.afterCountChanged();
      } else if (status === 'success') {
        this.successCount.next(this.successCount.value + 1);
        this.runningCount.next(this.runningCount.value - 1);
        this.afterCountChanged();
      } else if (status === 'failed') {
        this.failedCount.next(this.failedCount.value + 1);
        this.runningCount.next(this.runningCount.value - 1);
        this.afterCountChanged();
      }
    });

    this.getChangeJobObservable().pipe(
      filter(event => event.object.details.type === 'status'),
      filter(event => event.object.details.value !== 'created'),
    ).subscribe((event) => {
      console.log('Event', event);
      const tasks: TaskRaw[] = this.tasks.value.slice();
      const index = tasks.findIndex(item => item.id === event.object.id);
      if (index >= 0) {
        const task: TaskRaw = Object.assign({}, tasks[index]);
        task.status = event.object.details.value;
        console.log('Task changed', task);
        tasks.splice(index, 1, task);
        this.tasks.next(tasks);
      } else {
        this.taskService.get(event.object.id).subscribe((task) => {
          console.log(task);
          task.status = event.object.details.value;
          tasks.unshift(task);
          this.tasks.next(tasks);
        });
      }
    });
  }

  getCurrentCounts(): Observable<{ running: number, success: number, failed: number }> {
    const defaultParams = {
      limit: '1',
      offset: '0',
    };

    return zip(
      this.taskService.list({
        status: 'running',
        ...defaultParams,
      }),
      this.taskService.list({
        status: 'success',
        ...defaultParams,
      }),
      this.taskService.list({
        status: 'failed',
        ...defaultParams,
      }),
    ).pipe(
      map(
        ([runningList, successList, failedList]) => ({
          running: runningList.count,
          success: successList.count,
          failed: failedList.count,
        })
      )
    );
  }

  getLastTasks(): Observable<Task[]> {
    return zip(
      this.taskService.list({ ordering: '-finish_date', status: 'failed', limit: '5' }),
      this.taskService.list({ ordering: '-finish_date', status: 'success', limit: '5' }),
      this.taskService.list({ ordering: '-start_date', status: 'running', limit: '5' }),
    ).pipe(map(([failed, succeed, running]) => {
      return [...failed.results, ...succeed.results, ...running.results].sort((a, b) => {
        const getDateField = (task: Task) => task.status === 'failed' || task.status === 'success' ? task.finish_date : task.start_date;
        const aDate = new Date(getDateField(a));
        const bDate = new Date(getDateField(b));
        return aDate.getDate() - bDate.getDate();
      }).slice(0, 5);
    }));
  }

  ngAfterViewInit(): void {
    interval(200).pipe(
      this.takeUntil(),
      takeWhile(() => !this.animationElem.value),
    ).subscribe(() => {
      this.animationElem.next(this.animationRef ? this.animationRef.nativeElement : null);
    });

    this.animationElem.pipe(
      this.takeUntil(),
      filter((elem) => !!elem),
      take(1),
    ).subscribe(() => {
      zip(this.getCurrentCounts(), this.getLastTasks())
        .subscribe(([counts, tasks]) => {
          this.runningCount.next(counts.running);
          this.successCount.next(counts.success);
          this.failedCount.next(counts.failed);
          this.afterCountChanged();
          this.tasks.next(tasks);
          this.listenToJobs();
        });
    });

    this.isAnimationRunning.pipe(
      this.takeUntil(),
      filter(isRunning => !isRunning),
    ).subscribe(() => this.endAnimation());

    combineLatest(this.runningCount, this.successCount, this.failedCount)
      .pipe(this.takeUntil())
      .subscribe(
        ([runningCount, successCount, failedCount]) => this.counts.next({
          runningCount,
          successCount,
          failedCount,
        })
      );
  }

}
