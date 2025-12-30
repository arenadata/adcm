# ADCM Code Style

> Version: 0.1.0

ADCM is not a young project and has passed several shifts in code and architecture styles.

This document aims to set direction and rules for how we write and organize code.

Statements in here are about how it should be, not how it is now.

## Architecture

> Status: STABILIZATION

Described in here is an idea, based on previous refactoring stages.
If status is approved, we will move in this direction and all new features/code must at least not contradict that.

Conceptually, there are 4 major components of application:
1. Core / services
2. Repository / services implementations
3. Use cases
4. Controllers / entry points

### Core

Packages: `core`

"Clean" code that has no "big framework"/infra dependencies and little dependencies between core parts.

Core includes:
1. Generic-purpose code like `Success`/`Fail` concepts, that are used within whole codebase
2. Universal (yet project specific) modules like `types`, `errors`
3. Services:
  1. Generic mechanism shared by multiple features (e.g. `templates`)
  2. Per aspect/feature/component of ADCM (e.g. `config`, `mapping`)
  3. Multi-aspect services, using previous level services 
     due to their own complexity or business logic (e.g. `bundle`, `action`);
     may be named `scanario`s if have no own identity, simply uniting other services.
4. Infra dependencies interfaces

### Generic Modules

Concepts that are used on core level and above, depending only on Python.

#### Universal Modules

Universal modules shouldn't be dumpsters for all shared types, because they aren't the way of solving inter-service dependencies:
there shouldn't be any, but if required, should be solved in by-case manner.

Examples of universal type are `Descriptor` and enums like `ADCMCoreType`.

#### Services

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

#### Infra Dependencies

Interfaces for repos and stuff outside of service's responsibility.

Usually placed within service's package.

#### Inter-Service Dependencies

There shouldn't be any, except:
1. Special Service may depend on Generic Service
2. Dependency is based on business AND we've decided it'll ease everything without harm (avoid it until you can't)

One way to implement operations that require multiple dependencies is to create `scenario` 
which is a funciton or class (for DI convenience) that takes multiple independant services 
and calls them in order to implement repeatable operation.

### Implementations

Framework/infrastructure dependant code.

### Entry Points

Entry point (a.k.a. controller) is the orchestrator/configurator of use cases (provides implementations for use cases).

Our entry points are and their corresponding directories:
1. REST API (`api_v2`)
2. Job Runner (`task_runner.py`)
3. Ansible Plugins (`ansible`, `ansible_plugin`)
4. Django commands (`cm`, `audit`, `rbac`)

For now we delegate use cases configurations to DI and entrypoints provide only validation of inputs and calls to DI.

## Code

> Status: IN PROGRESS

### Project

> what and where

### Project -> Module -> Function

#### Public/Private API

#### Module Structure 

### Linters

We use:
- `ruff` for code formatting and linting
- `pyright` for typechecking
- `import-linter` for declaring layers in project and within packages

Silencing linters is generally disallowed.
Do it only when you absolutely have to and provide comment explaining the silencing.
