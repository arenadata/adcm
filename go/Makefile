ADCM = adcm

all: build

run:
	cd $(ADCM); go run runstatus.go

fmt:
	gofmt -w -s $(ADCM)/*.go
	gofmt -w -s $(ADCM)/status/*.go

lint:
	cd $(ADCM); golangci-lint run

build:
	cd $(ADCM); go mod tidy && go build -o ../bin/runstatus runstatus.go
