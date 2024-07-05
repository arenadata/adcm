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
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/gorilla/websocket"
)

const (
	writeWait  = 10 * time.Second
	pongWait   = 60 * time.Second
	pingPeriod = 50 * time.Second
)

type wsMsg interface {
	encode() ([]byte, error)
}

type wsClient struct {
	ws   *websocket.Conn
	send chan wsMsg
}

type wsHub struct {
	clients    map[*wsClient]bool
	register   chan *wsClient
	unregister chan *wsClient
	broadcast  chan wsMsg
}

var upgrader = websocket.Upgrader{
	CheckOrigin:  checkOrigin,
	Subprotocols: []string{"adcm"},
}

func newWSClient(ws *websocket.Conn) *wsClient {
	return &wsClient{
		ws:   ws,
		send: make(chan wsMsg),
	}
}

func newWsHub() *wsHub {
	return &wsHub{
		broadcast:  make(chan wsMsg),
		register:   make(chan *wsClient),
		unregister: make(chan *wsClient),
		clients:    make(map[*wsClient]bool),
	}
}

func (h *wsHub) run() {
	for {
		select {
		case ws := <-h.register:
			logg.D.l("wsHub register: ", ws)
			h.clients[ws] = true
		case ws := <-h.unregister:
			logg.D.l("wsHub unregister: ", ws)
			if _, ok := h.clients[ws]; ok {
				delete(h.clients, ws)
				close(ws.send)
			}
		case msg := <-h.broadcast:
			logg.D.f("wsHub broadcast: %v", msg)
			for ws := range h.clients {
				ws.send <- msg
			}
		}
	}
}

func (h *wsHub) send2ws(s wsMsg) {
	//logg.D.f("enter send2ws: %v", s)
	h.broadcast <- s
}

func write2ws(c *wsClient) {
	ticker := time.NewTicker(pingPeriod)
	defer func() { ticker.Stop() }()
	for {
		select {
		case s, ok := <-c.send:
			if !ok {
				logg.D.l("write2ws chanel closed")
				return
			}
			logg.D.l("write2ws recive: ", s)
			c.ws.SetWriteDeadline(time.Now().Add(writeWait)) //nolint: errcheck
			js, err := s.encode()
			if err != nil {
				logg.E.l("write2ws incorrect json: ", s)
				continue
			}
			if err := c.ws.WriteMessage(websocket.TextMessage, js); err != nil {
				logg.W.l("write2ws write: ", err)
				c.ws.Close()
				return
			}
		case <-ticker.C:
			c.ws.SetWriteDeadline(time.Now().Add(writeWait)) //nolint: errcheck
			if err := c.ws.WriteMessage(websocket.PingMessage, nil); err != nil {
				return
			}
		}
	}
}

func read4ws(h *wsHub, c *wsClient) {
	c.ws.SetReadLimit(256)
	c.ws.SetReadDeadline(time.Now().Add(pongWait)) //nolint: errcheck
	c.ws.SetPongHandler(func(string) error {
		c.ws.SetReadDeadline(time.Now().Add(pongWait)) //nolint: errcheck
		return nil
	})
	for {
		_, _, err := c.ws.ReadMessage()
		if err != nil {
			logg.I.f("read2ws client %v close ws: %v", c, err)
			h.unregister <- c
			c.ws.Close()
			return
		}
	}
}

func initWS(h *wsHub, w http.ResponseWriter, r *http.Request) {
	ws, err := upgrader.Upgrade(w, r, nil)
	logg.D.l("initWs open ws")
	if err != nil {
		logg.E.l("initWs upgrade: ", err)
		return
	}

	defer func() {
		logg.D.l("initWs close ws")
		ws.Close()
	}()

	client := newWSClient(ws)
	h.register <- client

	go read4ws(h, client)
	write2ws(client)
}

func checkOrigin(r *http.Request) bool {
	origin := r.Header["Origin"]
	if len(origin) == 0 {
		return true
	}
	u, err := url.Parse(origin[0])
	if err != nil {
		return false
	}
	s1 := strings.Split(u.Host, ":")
	s2 := strings.Split(r.Host, ":")
	logg.D.f("checkOrigin origin host: %v, header host: %v", u.Host, r.Host)
	if s1[0] == s2[0] {
		return true
	} else {
		return false
	}
}
