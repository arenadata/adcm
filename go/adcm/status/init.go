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

	router.GET("/api/v1/log/", authWrap(hub, showLogLevel))
	router.POST("/api/v1/log/", authWrap(hub, postLogLevel, false))

	router.POST("/api/v1/event/", authWrap(hub, postEvent))

	router.GET("/api/v1/all/", authWrap(hub, showAll))

	router.GET("/api/v1/host/", authWrap(hub, hostList))
	router.GET("/api/v1/host/:hostid/", authWrap(hub, showHost))
	router.POST("/api/v1/host/:hostid/", authWrap(hub, setHost))

	router.GET("/api/v1/object/host/", authWrap(hub, listHost))
	router.POST("/api/v1/object/host/", authWrap(hub, createHost))
	router.GET("/api/v1/object/host/:hostid/", authWrap(hub, retrieveHost))
	router.PUT("/api/v1/object/host/:hostid/", authWrap(hub, updateHost))

	router.GET("/api/v1/host/:hostid/component/:compid/", authWrap(hub, showHostComp))
	router.POST("/api/v1/host/:hostid/component/:compid/", authWrap(hub, setHostComp, false))

	router.GET("/api/v1/component/:compid/", authWrap(hub, showComp))

	router.GET("/api/v1/cluster/", authWrap(hub, clusterList))
	router.GET("/api/v1/cluster/:clusterid/", authWrap(hub, showCluster))
	router.GET("/api/v1/cluster/:clusterid/service/:serviceid/", authWrap(hub, showService))
	router.GET(
		"/api/v1/cluster/:clusterid/service/:serviceid/component/:compid/",
		authWrap(hub, showComp),
	)

	router.GET("/api/v1/servicemap/", authWrap(hub, showServiceMap))
	router.POST("/api/v1/servicemap/", authWrap(hub, postServiceMap))
	router.POST("/api/v1/servicemap/reload/", authWrap(hub, readConfig))

	log.Fatal(http.ListenAndServe(httpPort, router))
}

func authWrap(hub Hub, f func(h Hub, w http.ResponseWriter, r *http.Request), allow_adcm_session_optional ...bool) http.HandlerFunc {
    allow_adcm_session := true
    if len(allow_adcm_session_optional) > 0 {
        allow_adcm_session = allow_adcm_session_optional[0]
    }
	return func(w http.ResponseWriter, r *http.Request) {
		if !tokenAuth(w, r, hub, allow_adcm_session) {
			return
		}
		f(hub, w, r)
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
