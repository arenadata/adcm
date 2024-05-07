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

package main

import (
	"adcm/status"
	"flag"
	"os"
)

func main() {
	fileAuthKey := flag.String("secretfile",
		"/adcm/data/var/secrets.json",
		"Path to json config with secrets")
	logFile := flag.String("logfile", "", "log file name (with full path)")
	help := flag.Bool("help", false, "Print usage")
	flag.Parse()
	if *help {
		flag.PrintDefaults()
		os.Exit(0)
	}

	status.Start(status.ReadSecret(fileAuthKey), *logFile, status.GetLogLevel())
}
