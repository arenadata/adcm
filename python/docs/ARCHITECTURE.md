# ADCM Architecture

> Version: 0.2.0

> Status: STABILIZATION

This document aims to set direction and rules for how we write and organize code.

Statements in here are about how it should be, not how it is now.

Described in here is an idea, based on previous refactoring stages.
If status is approved, we will move in this direction and all new features/code must at least not contradict that.

Conceptually, there are 4 major components of application:
1. Core / services
2. Repository / services implementations
3. Use cases
4. Controllers / entry points

## Core

Packages: `core`

Code representing domain specific rules, services and instruments to work with them.

It must stay independant from structure-dictating frameworks and infrastracture specifics as much as possible and reasonable.

Core includes:
1. Generic-purpose code like `Success`/`Fail` concepts, that are used within whole codebase
2. Universal (yet project specific) modules like `types`, `errors`
3. Services:
    1. Generic mechanism shared by multiple features (e.g. `templates`)
    2. Per aspect/feature/component of `ADCM` (e.g. `config`, `mapping`)
    3. Multi-aspect services, using previous level services 
       due to their own complexity or business logic (e.g. `bundle`, `action`);
       may be named `scanario`s if have no own identity, simply uniting other services.
4. Infra dependencies interfaces

## Generic Modules

Concepts that are used on core level and above, depending only on `Python`.

### Universal Modules

Universal modules shouldn't be dumpsters for all shared types, because they aren't the way of solving inter-service dependencies:
there shouldn't be any, but if required, should be solved in by-case manner.

Examples of universal type are `Descriptor` and enums like `ADCMCoreType`.

### Services

Special (aspect/feature) services usually will have two parts:
1. Top level API:
   public interface defining infra dependencies 
   (e.g. `XService` class dependant on `FileStorageI` and `XRepoI` protocols via constructor).
   Usually that's what will be called outside of core (e.g. in use cases).
2. Low-level API:
   also known as rules.
   Usually functions that check, change, compare entities, yet never working with external interfaces:
   all required data must be provided via arguments.

Generic services should be self-contained, covering small, but meaningful part of functionality.
They may won't usually depend on other services, 
yet must be configurable enough in order to provide "whole" and "consistent" functionality.
It can be achieved with standalone protocols, specifying callables, etc., 
but infra interfaces shouldn't be required "by design".

---

Top level API of special services will usually be represented with class that:
- have depdencies provided via constructor and available for all methods;
- have public methods that ARE public API and take call-related arguments.

### Infra Dependencies

Interfaces for repos and stuff outside of service's responsibility.

Usually placed within service's package.

### Inter-Service Dependencies

There shouldn't be any, except:
1. Special Service may depend on Generic Service
2. Dependency is based on business AND we've decided it'll ease everything without harm (avoid it until you can't)

One way to implement operations that require multiple dependencies is to create `scenario` 
which is a funciton or class (for DI convenience) that takes multiple independant services 
and calls them in order to implement repeatable operation.

## Implementations

Framework/infrastructure dependant code.

## Use Cases

A use case orchestrates core services to satisfy a specific request coming from an entry point.

It accepts the minimal data required to complete its task, performs it, and signals success/failure to the caller.
It has no knowledge of presentation concerns (e.g. HTTP status codes, API response shape).
When required, should return details about performed operation.

IO effects should be encapsulated as much as possible and reasonable: no direct prints (logging at max) or current process control.
Such things should be left for controller to decide.
Example:
exceptions that map to a response code are raised and handled only at the entry point (presentation) layer, never within a use case.

## Entry Points

Entry point (a.k.a. controller) is the orchestrator/configurator of use cases (provides implementations for use cases).

Our entry points are and their corresponding directories:
1. REST API (`api_v2/`)
2. Job Runner (`task_runner.py`)
3. Ansible Plugins (`ansible/`, `ansible_plugin/`)
4. Django commands (`cm/`, `audit/`, `rbac/`)
5. Startup scripts (`application/`, `init_db.py`)

For now we delegate use cases configurations to DI and entrypoints provide only validation of inputs and calls to DI.

### REST API (Django)

Within the REST API entry point (`api_v2`), responsibility is split as:
- **Serializer** - validates request/response data. 
  Shouldn't access database as general rule.
  Direct querying is fobidden.
  May do implicit requests (queryset access) in existing code and for response serializers when it's most adequate way to serialize.
- **View** - checks permissions, extracts validated data from the serializer, determines which use case to call and prepares its arguments, then reacts to the use case's result. 
  May access the database to fetch/check objects referenced directly by the request.
- **Use case** - see [Use Cases](#use-cases) above.
