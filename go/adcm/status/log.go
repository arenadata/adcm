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
	"errors"
	"fmt"
	"log"
	"os"
	"sync"
// 	"time"
)

type logger struct {
	D        logWrapper
	I        logWrapper
	W        logWrapper
	E        logWrapper
	level    *int
	levelMap map[string]int
}

type logWrapper struct {
	out     logWriter
	log     *log.Logger
	level   int
	current *int
}

const (
	DEBUG = 1
	INFO  = 2
	WARN  = 3
	ERR   = 4
	CRIT  = 5
)

var logg logger

func (log *logger) decodeLogLevel(level string) (int, error) {
	intLevel, ok := log.levelMap[level]
	if !ok {
		return 0, errors.New("Unknown log level: " + level)
	}
	return intLevel, nil
}

func (log *logger) getLogLevel() string {
	for strLevel, intLevel := range log.levelMap {
		if intLevel == *log.level {
			return strLevel
		}

	}
	return "none"
}

func (log *logger) rotate() {
	log.E.out.Rotate()
}

func (log *logger) set(level int) {
	*log.level = level
	log.W.l("set log level to \"" + log.getLogLevel() + "\"")
}

func (log *logWrapper) l(v ...interface{}) {
	if log.level < *log.current {
		return
	}
	log.log.Println(v...)
}

func (log *logWrapper) f(format string, v ...interface{}) {
	if log.level < *log.current {
		return
	}
	log.log.Printf(format, v...)
}

func initLog(logFile string, level string) {
	logg = logger{}
	var out logWriter
	logg.levelMap = map[string]int{
		"debug":   DEBUG,
		"info":    INFO,
		"warning": WARN,
		"error":   ERR,
	}
	logLevel, err := logg.decodeLogLevel(level)
	if err != nil {
		fmt.Println(err.Error())
		os.Exit(1)
	}
	if logFile == "" {
		out = newStdoutWriter()
	} else {
		out = newRotateWriter(logFile)
	}
	logg.level = &logLevel
	logg.D = newLog(out, &logLevel, DEBUG, "[DEBUG] ")
	logg.I = newLog(out, &logLevel, INFO, "[INFO]  ")
	logg.W = newLog(out, &logLevel, WARN, "[WARN]  ")
	logg.E = newLog(out, &logLevel, ERR, "[ERROR] ")
}

func newLog(out logWriter, current *int, level int, tag string) logWrapper {
	return logWrapper{
		out:     out,
		level:   level,
		current: current,
		log:     log.New(out, tag, log.Ldate|log.Lmicroseconds|log.Lshortfile),
	}
}

type logWriter interface {
	Write(output []byte) (int, error)
	Rotate()
}

type stdoutWriter struct {
	fp *os.File
}

func newStdoutWriter() *stdoutWriter {
	return &stdoutWriter{fp: os.Stdout}
}

func (w *stdoutWriter) Write(output []byte) (int, error) {
	return w.fp.Write(output)
}

func (w *stdoutWriter) Rotate() {
}

// Rotatable Writer

type rotateWriter struct {
	lock     sync.Mutex
	filename string
	fp       *os.File
}

func newRotateWriter(filename string) *rotateWriter {
	w := rotateWriter{filename: filename}
	w.Rotate()
	return &w
}

func (w *rotateWriter) Write(output []byte) (int, error) {
	w.lock.Lock()
	defer w.lock.Unlock()
	return w.fp.Write(output)
}

func (w *rotateWriter) Rotate() {
	var err error
	w.lock.Lock()
	defer w.lock.Unlock()

    // ADCM-3242
	w.fp, err = os.OpenFile(w.filename, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
	    log.Fatalf("error opening log file %s: %v", w.filename, err)
	}
}
