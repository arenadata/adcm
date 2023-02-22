import { HttpClient } from '@angular/common/http';
import { Inject, Injectable } from '@angular/core';
import { Store } from '@ngrx/store';
import { Observable, OperatorFunction, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { authFailed } from '../store/auth/auth.actions';
import { DjangoHttpErrorResponse } from '../models/django-http-error-response';
import { NotificationService } from './notification.service';
import { ApiOptions } from '../models/api-options';
import { ApiConfigService } from '../api/api-config.service';
import { ApiConfig } from '../api/api-config';

@Injectable()
export class ApiService {

  constructor(
    private http: HttpClient,
    private store: Store,
    private notificationService: NotificationService,
    @Inject(ApiConfigService) public config: ApiConfig,
  ) {}

  protected authBehaviour<T>(): OperatorFunction<T, T>  {
    return catchError((err: DjangoHttpErrorResponse) => {
      if (err.status === 401) {
        this.store.dispatch(authFailed({ message: err.error.desc }));
      }
      return throwError(err);
    });
  }

  protected errorBehaviour<T>(options?: ApiOptions): OperatorFunction<T, T> {
    return catchError((err: DjangoHttpErrorResponse) => {
      if (!options || !options.ignoreErrors || options.ignoreErrors.every(ignoredError => ignoredError !== err.status)) {
        this.notificationService.error(`${err.status} - ${err.statusText}`);
      }
      return throwError(err);
    });
  }

  protected prepareUrl(url: string, options: ApiOptions): string {
    if (options && options.root) {
      return `/${options.root}/${url}/`;
    }
    return `/${this.config.defaultRoot}/${url}/`;
  }

  get<T>(url: string, options?: ApiOptions): Observable<T> {
    return this.http.get<T>(this.prepareUrl(url, options), options).pipe(
      this.authBehaviour<T>(),
      this.errorBehaviour<T>(options),
    );
  }

  post<T>(url: string, data: any = {}, options?: ApiOptions): Observable<T> {
    return this.http.post<T>(this.prepareUrl(url, options), data, options).pipe(
      this.authBehaviour<T>(),
      this.errorBehaviour<T>(options),
    );
  }

  put<T>(url: string, data: any = {}, options?: ApiOptions): Observable<T> {
    return this.http.put<T>(this.prepareUrl(url, options), data, options).pipe(
      this.authBehaviour<T>(),
      this.errorBehaviour<T>(options),
    );
  }

  patch<T>(url: string, data: any = {}, options?: ApiOptions): Observable<T> {
    return this.http.patch<T>(this.prepareUrl(url, options), data, options).pipe(
      this.authBehaviour<T>(),
      this.errorBehaviour<T>(options),
    );
  }

  delete(url: string, options?: ApiOptions): Observable<any> {
    return this.http.delete(this.prepareUrl(url, options)).pipe(
      this.authBehaviour(),
      this.errorBehaviour(options),
    );
  }

}
