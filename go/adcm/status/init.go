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
package status

import (
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/bouk/httprouter"
)

const httpPort = ":8020"
const componentTimeout = 300 // seconds

type Hub struct {
	HostStatusStorage    *Storage
	HostComponentStorage *Storage
	HostStorage          *HostStorage
	ServiceMap           *ServiceServer
	EventWS              *wsHub
	StatusEvent          *StatusEvent
	AdcmApi              *AdcmApi
	Secrets              *SecretConfig
}

func Start(secrets *SecretConfig, logFile string, logLevel string) {
	hub := Hub{Secrets: secrets}
	initLog(logFile, logLevel)
	initSignal()

	hub.HostComponentStorage = newStorage(dbMap2{}, "HostComponent")
	go hub.HostComponentStorage.run()
	hub.HostComponentStorage.setTimeOut(componentTimeout)

	hub.HostStatusStorage = newStorage(dbMap2{}, "ClusterHost")
	go hub.HostStatusStorage.run()
	hub.HostStatusStorage.setTimeOut(componentTimeout)

	hub.HostStorage = newHostStorage(dbHost{}, "Host")
	go hub.HostStorage.run()

	hub.ServiceMap = newServiceServer()
	go hub.ServiceMap.run()

	hub.EventWS = newWsHub()
	go hub.EventWS.run()

	hub.AdcmApi = newAdcmApi(secrets)
	go func() {
		time.Sleep(time.Second)
		hub.AdcmApi.getServiceMap()
	}()

	hub.StatusEvent = newStatusEvent()

	startHTTP(httpPort, hub)
}

func startHTTP(httpPort string, hub Hub) {
	logg.I.f("start http server on %s", httpPort)

	router := httprouter.New()
	router.RedirectTrailingSlash = false

	router.GET("/", index)
	router.GET("/api/v1/", apiRoot)

	router.GET("/ws/event/", func(w http.ResponseWriter, r *http.Request) {
		if !wsTokenAuth(w, r, hub) {
			return
		}
		initWS(hub.EventWS, w, r)
	})

	router.GET("/api/v1/log/", authWrap(hub, showLogLevel, AUTHCHECKANY, isADCMInternal, isStatusUser))
	router.POST("/api/v1/log/", authWrap(hub, postLogLevel, AUTHCHECKANY, isADCMInternal, isStatusUser))

	router.POST("/api/v1/event/", authWrap(hub, postEvent, AUTHCHECKANY, isADCMInternal, isStatusChecker, isStatusUser))

	router.GET("/api/v1/all/", authWrap(hub, showAll, AUTHCHECKANY, isADCMInternal, isStatusUser, isADCMUser))

	router.GET("/api/v1/host/", authWrap(hub, hostList, AUTHCHECKANY, isADCMInternal, isStatusUser, isADCMUser))
	router.GET("/api/v1/host/:hostid/", authWrap(hub, showHost, AUTHCHECKANY, isADCMInternal, isStatusUser, isADCMUser))
	router.POST("/api/v1/host/:hostid/", authWrap(hub, setHost, AUTHCHECKANY, isADCMInternal, isStatusChecker))

	router.GET("/api/v1/object/host/", authWrap(hub, listHost, AUTHCHECKANY, isADCMInternal, isStatusUser))
	router.POST("/api/v1/object/host/", authWrap(hub, createHost, AUTHCHECKANY, isADCMInternal, isStatusUser))
	router.GET("/api/v1/object/host/:hostid/", authWrap(hub, retrieveHost, AUTHCHECKANY, isADCMInternal, isStatusUser))
	router.PUT("/api/v1/object/host/:hostid/", authWrap(hub, updateHost, AUTHCHECKANY, isADCMInternal, isStatusUser))

	router.GET("/api/v1/host/:hostid/component/:compid/", authWrap(hub, showHostComp, AUTHCHECKANY, isADCMInternal, isStatusUser, isADCMUser))
	router.POST("/api/v1/host/:hostid/component/:compid/", authWrap(hub, setHostComp, AUTHCHECKANY, isADCMInternal, isStatusChecker))

	router.GET("/api/v1/component/:compid/", authWrap(hub, showComp, AUTHCHECKANY, isADCMInternal, isADCMUser))

	router.GET("/api/v1/cluster/", authWrap(hub, clusterList, AUTHCHECKANY, isADCMInternal, isADCMUser))
	router.GET("/api/v1/cluster/:clusterid/", authWrap(hub, showCluster, AUTHCHECKANY, isADCMInternal, isADCMUser))
	router.GET("/api/v1/cluster/:clusterid/service/:serviceid/", authWrap(hub, showService, AUTHCHECKANY, isADCMInternal, isADCMUser))
	router.GET(
		"/api/v1/cluster/:clusterid/service/:serviceid/component/:compid/",
		authWrap(hub, showComp, AUTHCHECKANY, isADCMInternal, isADCMUser),
	)

	router.GET("/api/v1/servicemap/", authWrap(hub, showServiceMap, AUTHCHECKANY, isADCMInternal, isStatusUser))
	router.POST("/api/v1/servicemap/", authWrap(hub, postServiceMap, AUTHCHECKANY, isADCMInternal, isStatusUser))
	router.POST("/api/v1/servicemap/reload/", authWrap(hub, readConfig, AUTHCHECKANY, isADCMInternal, isStatusUser))

	log.Fatal(http.ListenAndServe(httpPort, router))
}

func authWrap(hub Hub, f func(h Hub, w http.ResponseWriter, r *http.Request), authCheckOperator authCheckOperatorType, authCheckers ...authCheckerType) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
	    var checkResult bool
	    var allowed bool

	    for _, checkFunc := range authCheckers {
	        checkResult = checkFunc(r, hub)
	        if authCheckOperator == AUTHCHECKANY {
	            allowed = false
	            if checkResult {
	                allowed = true
	                break
	            }
	        } else if authCheckOperator == AUTHCHECKALL {
	            allowed = true
	            if !checkResult {
	                allowed = false
	                break
	            }
	        }
        }
	    if !allowed {
	        ErrOut4(w, r, "AUTH_ERROR", "forbidden for "+r.URL.Path)
	    } else {
		    f(hub, w, r)
		}
    }
}

func initSignal() {
	c := make(chan os.Signal, 1)
	signal.Notify(c, syscall.SIGUSR1)
	go func() {
		for {
			sig := <-c
			logg.D.f("recive signal %v", sig)
			logg.rotate()
		}
	}()
}
