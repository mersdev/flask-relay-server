# 🏗️ Architecture Documentation

## MVC Pattern & SOLID Principles

This document describes the architectural design of the Flask Relay Server, which follows the **Model-View-Controller (MVC)** pattern and adheres to **SOLID** principles for maintainability, testability, and extensibility.

---

## 📁 Project Structure

```
flask-relay-server/
├── app/                          # Main application package
│   ├── __init__.py              # Application factory
│   ├── config.py                # Configuration constants
│   │
│   ├── models/                  # MODEL LAYER
│   │   ├── __init__.py
│   │   ├── mailbox.py           # Mailbox entity & repository
│   │   └── device_claim.py      # Device claim entity & repository
│   │
│   ├── services/                # BUSINESS LOGIC LAYER
│   │   ├── __init__.py
│   │   ├── mailbox_service.py   # Mailbox business logic
│   │   ├── validation_service.py # Input validation
│   │   └── deduplication_service.py # Request deduplication
│   │
│   ├── controllers/             # CONTROLLER LAYER
│   │   ├── __init__.py
│   │   ├── mailbox_controller.py # Mailbox route handlers
│   │   └── health_controller.py  # Utility route handlers
│   │
│   └── views/                   # VIEW LAYER
│       ├── __init__.py
│       └── response_builder.py  # Response formatting
│
├── app.py                       # Application entry point
├── crypto_utils.py              # Encryption utilities
├── streamlit_app.py             # Streamlit frontend
├── test_workflows.py            # Test suite
├── requirements.txt             # Dependencies
├── README.md                    # User documentation
├── BEST_PRACTICES.md            # Code quality guide
└── ARCHITECTURE.md              # This file
```

---

## 🎯 MVC Pattern Implementation

### Model Layer (Data & Domain Logic)

**Location:** `app/models/`

**Responsibility:** Data structures, domain entities, and data access

#### Components:

1. **Mailbox Model** (`mailbox.py`)
   - `Mailbox`: Entity representing a mailbox
   - `MailboxConfiguration`: Configuration dataclass
   - `MailboxRepository`: Data access layer
   - `create_mailbox_from_request()`: Factory function

2. **Device Claim Model** (`device_claim.py`)
   - `DeviceClaim`: Entity for device authorization
   - `DeviceClaimRepository`: Data access layer

**Key Features:**
- ✅ Dataclasses for clean, immutable data
- ✅ Repository pattern for data access abstraction
- ✅ Domain logic methods (e.g., `is_expired()`, `has_access_right()`)
- ✅ Factory functions for object creation

**Example:**
```python
@dataclass
class Mailbox:
    mailbox_id: str
    payload: Dict[str, str]
    display_information: Dict[str, str]

    def is_expired(self) -> bool:
        """Domain logic in the model"""
        ...
```

### View Layer (Presentation)

**Location:** `app/views/`

**Responsibility:** Format responses for the client

#### Components:

1. **ResponseBuilder** (`response_builder.py`)
   - Formats all API responses
   - Handles JSON and HTML responses
   - Centralizes response structure

**Key Features:**
- ✅ Single place for response formatting
- ✅ Consistent response structure
- ✅ XSS protection for HTML responses
- ✅ Type-safe response building

**Example:**
```python
class ResponseBuilder:
    @staticmethod
    def success(data: Dict, status_code: int) -> Tuple[Response, int]:
        return jsonify(data), status_code

    @staticmethod
    def error(message: str, status_code: int) -> Tuple[Response, int]:
        return jsonify({"error": message}), status_code
```

### Controller Layer (Request Handling)

**Location:** `app/controllers/`

**Responsibility:** Handle HTTP requests, coordinate between services and views

#### Components:

1. **MailboxController** (`mailbox_controller.py`)
   - Handles all mailbox-related endpoints
   - Validates requests
   - Coordinates with services
   - Returns formatted responses

2. **HealthController** (`health_controller.py`)
   - Health check endpoint
   - API information endpoint

**Key Features:**
- ✅ Thin controllers (logic delegated to services)
- ✅ Request validation
- ✅ Error handling
- ✅ Response formatting delegation

**Example:**
```python
class MailboxController:
    def __init__(self, mailbox_service, validation_service, deduplication_service):
        self._mailbox_service = mailbox_service
        self._validation_service = validation_service
        self._deduplication_service = deduplication_service

    def create_mailbox(self) -> Tuple[Any, int]:
        # 1. Validate request
        # 2. Call service
        # 3. Return formatted response
        ...
```

---

## 🔧 Service Layer (Business Logic)

**Location:** `app/services/`

**Responsibility:** Business logic, orchestration, and complex operations

### Components:

1. **MailboxService** (`mailbox_service.py`)
   - Create, read, update, delete mailboxes
   - Device authorization
   - Receiver binding
   - Cleanup operations

2. **ValidationService** (`validation_service.py`)
   - Input validation
   - UUID validation
   - Payload structure validation

3. **DeduplicationService** (`deduplication_service.py`)
   - Request tracking
   - Duplicate detection

**Key Features:**
- ✅ Business logic separated from HTTP concerns
- ✅ Reusable across different interfaces (REST, GraphQL, etc.)
- ✅ Testable without HTTP infrastructure
- ✅ Clear dependencies via constructor injection

**Example:**
```python
class MailboxService:
    def __init__(self, mailbox_repo, device_claim_repo):
        self._mailbox_repo = mailbox_repo
        self._device_claim_repo = device_claim_repo

    def create_mailbox(self, payload, display_info, ...):
        # Business logic here
        ...
```

---

## 🎨 SOLID Principles

### 1. Single Responsibility Principle (SRP)

> Each class should have one, and only one, reason to change.

**Implementation:**

- **Mailbox Model**: Represents mailbox data only
- **MailboxRepository**: Handles data persistence only
- **MailboxService**: Coordinates mailbox operations only
- **ValidationService**: Validates input only
- **MailboxController**: Handles HTTP requests only
- **ResponseBuilder**: Formats responses only

**Example:**
```python
# ❌ BAD: Multiple responsibilities
class Mailbox:
    def save(self):  # Persistence
        ...
    def validate(self):  # Validation
        ...
    def to_json(self):  # Presentation
        ...

# ✅ GOOD: Single responsibility
class Mailbox:  # Data only
    ...

class MailboxRepository:  # Persistence only
    def save(self, mailbox):
        ...

class ValidationService:  # Validation only
    def validate(self, data):
        ...

class ResponseBuilder:  # Presentation only
    def to_json(self, mailbox):
        ...
```

### 2. Open/Closed Principle (OCP)

> Software entities should be open for extension but closed for modification.

**Implementation:**

- **New validation rules** can be added without modifying existing validators
- **New response types** can be added to ResponseBuilder without changing existing methods
- **New storage backends** can be added by implementing repository interface

**Example:**
```python
# ✅ GOOD: New validators can be added without modifying ValidationService
class ValidationService:
    @staticmethod
    def validate_uuid(uuid_string):  # Existing method - unchanged
        ...

    @staticmethod
    def validate_email(email):  # New validator - no existing code modified
        ...
```

### 3. Liskov Substitution Principle (LSP)

> Subtypes must be substitutable for their base types.

**Implementation:**

- **Repository pattern**: Any repository implementation can be swapped
- **Service interfaces**: Services can be replaced with mock implementations for testing

**Example:**
```python
# ✅ GOOD: Repositories are interchangeable
class MailboxRepository:
    def find_by_id(self, mailbox_id): ...

class InMemoryMailboxRepository(MailboxRepository):  # Can substitute
    def find_by_id(self, mailbox_id): ...

class PostgresMailboxRepository(MailboxRepository):  # Can substitute
    def find_by_id(self, mailbox_id): ...
```

### 4. Interface Segregation Principle (ISP)

> Clients should not be forced to depend on interfaces they don't use.

**Implementation:**

- **Controllers** depend only on the service methods they need
- **Services** depend only on the repository methods they need
- **Specialized services** (ValidationService, DeduplicationService) instead of one giant service

**Example:**
```python
# ❌ BAD: Giant interface
class AllInOneService:
    def create_mailbox(self): ...
    def validate_uuid(self): ...
    def deduplicate_request(self): ...
    def encrypt_data(self): ...

# ✅ GOOD: Segregated interfaces
class MailboxService:
    def create_mailbox(self): ...

class ValidationService:
    def validate_uuid(self): ...

class DeduplicationService:
    def deduplicate_request(self): ...
```

### 5. Dependency Inversion Principle (DIP)

> Depend on abstractions, not concretions.

**Implementation:**

- **Controllers** depend on service interfaces, not implementations
- **Services** depend on repository interfaces, not implementations
- **Dependency Injection** via constructor parameters

**Example:**
```python
# ✅ GOOD: Depends on abstractions (constructor injection)
class MailboxController:
    def __init__(
        self,
        mailbox_service: MailboxService,  # Abstract dependency
        validation_service: ValidationService,  # Abstract dependency
        deduplication_service: DeduplicationService  # Abstract dependency
    ):
        self._mailbox_service = mailbox_service
        self._validation_service = validation_service
        self._deduplication_service = deduplication_service

# Can easily swap implementations for testing
mock_mailbox_service = MockMailboxService()
controller = MailboxController(mock_mailbox_service, ...)
```

---

## 🏭 Application Factory Pattern

**Location:** `app/__init__.py`

**Purpose:** Creates and configures the application with all dependencies

### Benefits:

1. **Testability**: Easy to create test instances with mock dependencies
2. **Configuration**: Different configurations for development/production
3. **Dependency Management**: Central place for wiring dependencies
4. **Multiple Instances**: Can create multiple app instances if needed

### Implementation:

```python
def create_app() -> Flask:
    """Application factory function."""
    app = Flask(__name__)

    # Create repositories (Data Layer)
    mailbox_repository = MailboxRepository()
    device_claim_repository = DeviceClaimRepository()

    # Create services (Business Logic Layer)
    mailbox_service = MailboxService(mailbox_repository, device_claim_repository)
    validation_service = ValidationService()
    deduplication_service = DeduplicationService()

    # Create controllers (Presentation Layer)
    mailbox_controller = MailboxController(
        mailbox_service,
        validation_service,
        deduplication_service
    )

    # Register blueprints
    app.register_blueprint(create_mailbox_blueprint(mailbox_controller))

    return app
```

---

## 📊 Data Flow

### Request Flow (Create Mailbox Example):

```
1. HTTP Request
   ↓
2. Flask Route → MailboxController.create_mailbox()
   ↓
3. ValidationService.validate_create_mailbox_request()
   ↓
4. DeduplicationService.is_duplicate_request()
   ↓
5. MailboxService.create_mailbox()
   ↓
6. MailboxRepository.create()
   ↓
7. DeviceClaimRepository.create()
   ↓
8. ResponseBuilder.mailbox_created_response()
   ↓
9. HTTP Response
```

### Layer Responsibilities:

| Layer | Responsibilities | Dependencies |
|-------|-----------------|--------------|
| **Controller** | Request parsing, routing, response | Services, Views |
| **Service** | Business logic, orchestration | Models (Repositories) |
| **Model** | Data structure, domain logic, persistence | None (pure data) |
| **View** | Response formatting | None (pure formatting) |

---

## 🧪 Testing Strategy

### Unit Testing:

```python
# Test models in isolation
def test_mailbox_is_expired():
    mailbox = Mailbox(...)
    assert mailbox.is_expired() == True

# Test services with mock repositories
def test_mailbox_service_create():
    mock_repo = MockMailboxRepository()
    service = MailboxService(mock_repo, ...)
    result = service.create_mailbox(...)
    assert result is not None

# Test controllers with mock services
def test_mailbox_controller_create():
    mock_service = MockMailboxService()
    controller = MailboxController(mock_service, ...)
    response = controller.create_mailbox()
    assert response[1] == 200
```

---

## 🚀 Benefits of This Architecture

### 1. **Maintainability**
- Clear separation of concerns
- Easy to locate and fix bugs
- Changes in one layer don't affect others

### 2. **Testability**
- Each component can be tested in isolation
- Easy to mock dependencies
- Fast unit tests without HTTP infrastructure

### 3. **Scalability**
- Easy to add new features
- Can swap implementations (e.g., in-memory → PostgreSQL)
- Multiple developers can work on different layers

### 4. **Readability**
- Clear structure and organization
- Each file has a single purpose
- Easy for new developers to understand

### 5. **Reusability**
- Services can be reused across different controllers
- Models can be reused across different services
- Validation logic centralized and reusable

---

## 📝 Adding New Features

### Example: Adding a New Endpoint

1. **Model Layer** (if needed)
   ```python
   # app/models/new_entity.py
   @dataclass
   class NewEntity:
       ...
   ```

2. **Service Layer**
   ```python
   # app/services/new_service.py
   class NewService:
       def __init__(self, repo):
           self._repo = repo

       def perform_operation(self):
           ...
   ```

3. **Controller Layer**
   ```python
   # app/controllers/new_controller.py
   class NewController:
       def __init__(self, new_service):
           self._service = new_service

       def handle_request(self):
           ...
   ```

4. **Wire Dependencies**
   ```python
   # app/__init__.py
   def create_app():
       ...
       new_service = NewService(repo)
       new_controller = NewController(new_service)
       app.register_blueprint(create_new_blueprint(new_controller))
       ...
   ```

---

## 🎓 Key Takeaways

1. **MVC Pattern** provides clear separation between data, business logic, and presentation
2. **SOLID Principles** ensure code is maintainable, testable, and extensible
3. **Dependency Injection** makes components loosely coupled and easy to test
4. **Application Factory** centralizes configuration and dependency wiring
5. **Repository Pattern** abstracts data access for easy swapping of storage backends

This architecture makes the codebase:
- ✅ Easy to understand
- ✅ Easy to test
- ✅ Easy to maintain
- ✅ Easy to extend
- ✅ Production-ready

---

**For more details, see:**
- [BEST_PRACTICES.md](BEST_PRACTICES.md) - Code quality guidelines
- [README.md](README.md) - User documentation
