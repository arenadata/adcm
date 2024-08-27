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
)

type logger struct {
	D        logWrapper
	I        logWrapper
	W        logWrapper
	E        logWrapper
	C        logWrapper
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
	log.E.out.ReopenLogFile()
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
		"DEBUG":    DEBUG,
		"INFO":     INFO,
		"WARNING":  WARN,
		"ERROR":    ERR,
		"CRITICAL": CRIT,
	}
	logLevel, err := logg.decodeLogLevel(level)
	if err != nil {
		fmt.Println(err.Error())
		os.Exit(1)
	}
	if logFile == "" {
		out = newStdoutWriter()
	} else {
		out = newFileWriter(logFile)
	}
	logg.level = &logLevel
	logg.D = newLog(out, &logLevel, DEBUG, "[DEBUG] ")
	logg.I = newLog(out, &logLevel, INFO, "[INFO]  ")
	logg.W = newLog(out, &logLevel, WARN, "[WARN]  ")
	logg.E = newLog(out, &logLevel, ERR, "[ERROR] ")
	logg.C = newLog(out, &logLevel, CRIT, "[CRITICAL] ")
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
	ReopenLogFile()
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

func (w *stdoutWriter) ReopenLogFile() {
}

// File Writer

type fileWriter struct {
	lock     sync.Mutex
	filename string
	fp       *os.File
}

func newFileWriter(filename string) *fileWriter {
	w := fileWriter{filename: filename}
	w.ReopenLogFile()
	return &w
}

func (w *fileWriter) Write(output []byte) (int, error) {
	w.lock.Lock()
	defer w.lock.Unlock()
	return w.fp.Write(output)
}

func (w *fileWriter) ReopenLogFile() {
	var err error
	w.lock.Lock()
	defer w.lock.Unlock()

	w.fp, err = os.OpenFile(w.filename, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		log.Fatalf("error opening log file %s: %v", w.filename, err)
	}
}

func GetLogLevel() string {
	const defaultLogLevel = "ERROR"

	priorityLogLevel, ok := os.LookupEnv("STATUS_LOG_LEVEL")
	if ok {
		return priorityLogLevel
	}

	logLevel, ok := os.LookupEnv("LOG_LEVEL")
	if !ok {
		return defaultLogLevel
	}

	return logLevel
}
