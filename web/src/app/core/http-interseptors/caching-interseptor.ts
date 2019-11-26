// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
import { Injectable } from '@angular/core';
import { HttpInterceptor, HttpRequest, HttpResponse, HttpHandler, HttpHeaders, HttpEvent } from '@angular/common/http';
import { RequestCache } from './request-cache.service';
import { of, Observable } from 'rxjs';
import { startWith, tap } from 'rxjs/operators';

@Injectable()
export class CachingInterseptor implements HttpInterceptor {
  constructor(private cache: RequestCache) {}

  intercept(req: HttpRequest<any>, next: HttpHandler) {
    if (!isCachable(req)) return next.handle(req);

    const cachedResponse = this.cache.get(req);

    // cache-then-refresh
    if (req.headers.get('x-refresh')) {
      const results$ = sendRequest(req, next, this.cache);
      return cachedResponse ? results$.pipe(startWith(cachedResponse)) : results$;
    }

    return cachedResponse ? of(cachedResponse) : sendRequest(req, next, this.cache);
  }
}

function isCachable(req: HttpRequest<any>) {
  const method = req.method,
    url = req.url;
  return req.params.get('c') ? true : false;
}

function sendRequest(req: HttpRequest<any>, next: HttpHandler, cache: RequestCache): Observable<HttpEvent<any>> {
  const noHeaderClone = req.clone({ headers: new HttpHeaders() });

  return next.handle(noHeaderClone).pipe(
    tap(event => {
      if (event instanceof HttpResponse) cache.put(req, event);
    })
  );
}
