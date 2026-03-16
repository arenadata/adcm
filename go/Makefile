ADCM = adcm

all: build

run:
	cd $(ADCM); go run runstatus.go

pretty:
	gofmt -w -l -s $(ADCM)

lint:
	cd $(ADCM); golangci-lint run

build:
	cd $(ADCM); CGO_ENABLED=0 go mod tidy && CGO_ENABLED=0 go build -o ../bin/runstatus runstatus.go
