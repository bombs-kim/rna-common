"""
Server modules organized by domain/resource.

Each module encapsulates a coherent backend unit and is structured around
a clear separation of responsibilities:

- models.py
  Defines ORM models that represent database structure and relationships.
  These models may include domain-specific business logic implemented as
  model methods, such as state transitions, validations, and derived
  behaviors that naturally belong to the entity itself.

- crud.py
  Provides a collection of CRUD functions that operate on database objects.
  This layer is responsible only for persistence concerns such as creating,
  reading, updating, and deleting records, as well as simple filtering or
  lookup logic. It intentionally avoids higher-level business workflows,
  side effects, or cross-module coordination.

- schemas.py
  Defines schemas used for data exchange at external boundaries, including
  request and response payloads. These schemas serve as the contract between
  clients and the backend, handling validation and serialization without
  leaking internal ORM models.

- views.py
  Defines API endpoint handlers for the module. This layer receives validated
  input data, invokes model methods and CRUD functions as needed, and
  constructs responses using the defined schemas.

All modules are part of a single backend server, share the same database and
infrastructure, and are composed together at the API layer.
"""

# TODO Add validation logic
