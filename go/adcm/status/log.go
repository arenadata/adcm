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
	"fmt"
	"log"
	"os"
	"strings"
	"sync"
)

const DefaultLogLevel = "ERROR"

type simpleLogger interface {
	Println(v ...interface{})
	Printf(format string, v ...interface{})
}

type logHandler interface {
	Write(output []byte) (int, error)
	ReopenLogFile()
}

// Logger

type logger struct {
	D       simpleLogger
	I       simpleLogger
	W       simpleLogger
	E       simpleLogger
	C       simpleLogger
	handler logHandler
	level   string
}

func (l *logger) ReopenLogFile() {
	l.handler.ReopenLogFile()
}

func (l *logger) SetLogLevel(level string) error {
	createRealLogger := func(level string) *log.Logger {
		return log.New(
			l.handler,
			"["+strings.ToUpper(level)+"] ",
			log.Ldate|log.Lmicroseconds|log.Lshortfile,
		)
	}

	dummy := &dummyLogger{}

	switch level {
	case "DEBUG":
		l.D = createRealLogger("DEBUG")
		l.I = createRealLogger("INFO")
		l.W = createRealLogger("WARNING")
		l.E = createRealLogger("ERROR")
		l.C = createRealLogger("CRITICAL")
	case "INFO":
		l.D = dummy
		l.I = createRealLogger("INFO")
		l.W = createRealLogger("WARNING")
		l.E = createRealLogger("ERROR")
		l.C = createRealLogger("CRITICAL")
	case "WARNING":
		l.D = dummy
		l.I = dummy
		l.W = createRealLogger("WARNING")
		l.E = createRealLogger("ERROR")
		l.C = createRealLogger("CRITICAL")
	case "ERROR":
		l.D = dummy
		l.I = dummy
		l.W = dummy
		l.E = createRealLogger("ERROR")
		l.C = createRealLogger("CRITICAL")
	case "CRITICAL":
		l.D = dummy
		l.I = dummy
		l.W = dummy
		l.E = dummy
		l.C = createRealLogger("CRITICAL")
	default:
		return fmt.Errorf("unknown log level: %s", level)
	}
	l.level = level
	return nil
}

var logg logger

func InitLog(logFile string, level string) {
	logg = logger{}

	if logFile == "" {
		logg.handler = &stdOutHandler{fp: os.Stdout}
	} else {
		logg.handler = &fileHandler{filename: logFile}
		logg.handler.ReopenLogFile()
	}

	err := logg.SetLogLevel(level)
	if err != nil {
		if retryErr := logg.SetLogLevel(DefaultLogLevel); retryErr != nil {
			log.Fatalf("Failed to set level %q and fallback to default %q", level, DefaultLogLevel)
		}
	}
}

// Dummy Logger

type dummyLogger struct{}

func (dl *dummyLogger) Println(v ...interface{})                {}
func (dll *dummyLogger) Printf(format string, v ...interface{}) {}

// Handlers

type stdOutHandler struct {
	fp *os.File
}

func (w *stdOutHandler) Write(output []byte) (int, error) {
	return w.fp.Write(output)
}

func (w *stdOutHandler) ReopenLogFile() {
}

type fileHandler struct {
	lock     sync.Mutex
	filename string
	fp       *os.File
}

func (w *fileHandler) Write(output []byte) (int, error) {
	w.lock.Lock()
	defer w.lock.Unlock()
	return w.fp.Write(output)
}

func (w *fileHandler) ReopenLogFile() {
	var err error
	w.lock.Lock()
	defer w.lock.Unlock()

	w.fp, err = os.OpenFile(w.filename, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		log.Fatalf("Error opening log file %s: %v", w.filename, err)
	}
}
