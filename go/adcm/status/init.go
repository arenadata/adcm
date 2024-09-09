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
	ServiceMap           *ServiceServer
	EventWS              *wsHub
	StatusEvent          *StatusEvent
	AdcmApi              *AdcmApi
	Secrets              *SecretConfig
	MMObjects            *MMObjects
}

func Start(secrets *SecretConfig, logFile string, logLevel string) {
	hub := Hub{Secrets: secrets}
	InitLog(logFile, logLevel)
	initSignal()

	hub.MMObjects = newMMObjects()

	hub.HostComponentStorage = newStorage(dbMap2{}, "HostComponent")
	go hub.HostComponentStorage.run()
	hub.HostComponentStorage.setTimeOut(componentTimeout)

	hub.HostStatusStorage = newStorage(dbMap2{}, "ClusterHost")
	go hub.HostStatusStorage.run()
	hub.HostStatusStorage.setTimeOut(componentTimeout)

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
	logg.I.Printf("start http server on %s", httpPort)

	router := httprouter.New()
	router.RedirectTrailingSlash = false

	router.GET("/", index)
	router.GET("/api/v1/", apiRoot)

	router.GET("/ws/event/", func(w http.ResponseWriter, r *http.Request) {
		// If authentication with "regular" instruments work, we can init WS connection
		if isADCMUser(r, hub) || canAuthWithWebSocketHeaderCredentials(r, hub) {
			initWS(hub.EventWS, w, r)
			return
		}

		// Error otherwise
		ErrOut(w, r, "AUTH_ERROR")
	})

	router.GET("/api/v1/log/", authWrap(hub, showLogLevel, isADCM))
	router.POST("/api/v1/log/", authWrap(hub, postLogLevel, isADCM))

	router.POST("/api/v1/event/", authWrap(hub, postEvent, isADCM))

	router.GET("/api/v1/all/", authWrap(hub, showAll, isADCM, isADCMUser))

	router.GET("/api/v1/host/", authWrap(hub, hostList, isADCM, isADCMUser))
	router.GET("/api/v1/host/:hostid/", authWrap(hub, showHost, isStatusChecker, isADCM, isADCMUser))
	router.POST("/api/v1/host/:hostid/", authWrap(hub, setHost, isStatusChecker, isADCM))

	router.GET("/api/v1/object/mm/", authWrap(hub, getMMObjects, isADCM))
	router.POST("/api/v1/object/mm/", authWrap(hub, postMMObjects, isADCM))

	router.GET("/api/v1/host/:hostid/component/:compid/", authWrap(hub, showHostComp, isStatusChecker, isADCM, isADCMUser))
	router.POST("/api/v1/host/:hostid/component/:compid/", authWrap(hub, setHostComp, isStatusChecker, isADCM))

	router.GET("/api/v1/component/:compid/", authWrap(hub, showComp, isADCM, isADCMUser))

	router.GET("/api/v1/cluster/", authWrap(hub, clusterList, isADCM, isADCMUser))
	router.GET("/api/v1/cluster/:clusterid/", authWrap(hub, showCluster, isADCM, isADCMUser))
	router.GET("/api/v1/cluster/:clusterid/service/:serviceid/", authWrap(hub, showService, isADCM, isADCMUser))
	router.GET(
		"/api/v1/cluster/:clusterid/service/:serviceid/component/:compid/",
		authWrap(hub, showComp, isADCM, isADCMUser),
	)

	router.GET("/api/v1/servicemap/", authWrap(hub, showServiceMap, isADCM))
	router.POST("/api/v1/servicemap/", authWrap(hub, postServiceMap, isADCM))
	router.POST("/api/v1/servicemap/reload/", authWrap(hub, readConfig, isADCM))

	log.Fatal(http.ListenAndServe(httpPort, router))
}

func authWrap(hub Hub, f func(h Hub, w http.ResponseWriter, r *http.Request), authCheckers ...authCheckerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		allowed := false

		for _, checkFunc := range authCheckers {
			checkResult := checkFunc(r, hub)
			if checkResult {
				allowed = true
				break
			}
		}

		if !allowed {
			ErrOut4(w, r, "AUTH_ERROR", "forbidden")
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
			logg.D.Printf("Signal received %v", sig)
			logg.ReopenLogFile()
		}
	}()
}
