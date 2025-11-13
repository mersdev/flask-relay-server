# 🔐 Secure Credential Transfer Relay Server

A Flask-based implementation of the **Secure Credential Transfer** protocol based on [draft-secure-credential-transfer-04](https://datatracker.ietf.org/doc/html/draft-secure-credential-transfer-04).

This project provides a complete relay server for securely transferring digital credentials between devices, supporting both **stateless** and **stateful** workflows. Built with **MVC architecture** and following **SOLID principles** for maintainability, extensibility, and clean code.

## 📋 Features

### ✅ Complete API Implementation
- **CreateMailbox** - POST /v1/m
- **UpdateMailbox** - PUT /v1/m/{mailboxIdentifier}
- **DeleteMailbox** - DELETE /v1/m/{mailboxIdentifier}
- **ReadDisplayInformationFromMailbox** - GET /v1/m/{mailboxIdentifier}
- **ReadSecureContentFromMailbox** - POST /v1/m/{mailboxIdentifier}
- **RelinquishMailbox** - PATCH /v1/m/{mailboxIdentifier}

### 🔒 Security Features
- AES-GCM encryption (128-bit and 256-bit)
- Device claim-based authorization
- Request deduplication protection
- Automatic mailbox expiration
- Secure payload encryption/decryption

### 🎯 Workflow Support
- **Stateless Workflow**: Single credential transfer (Sender → Receiver)
- **Stateful Workflow**: Multiple round-trip exchanges for complex provisioning

### 🏗️ Architecture
- **MVC Pattern**: Clear separation of concerns (Model-View-Controller)
- **SOLID Principles**: Maintainable, extensible, testable code
- **Dependency Injection**: Loose coupling and easy testing
- **Repository Pattern**: Data access abstraction
- **Application Factory**: Flexible app configuration

### 🎨 Streamlit Frontend
- Interactive web interface for testing
- Separate interfaces for Sender and Receiver
- Real-time workflow demonstrations
- Built-in encryption/decryption utilities

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Installation

1. **Clone the repository**
   ```bash
   cd flask-relay-server
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

### Running the Server

#### Option 1: Using Start Scripts (Recommended)

**Start Flask Server:**
```bash
./start_server.sh
# or
chmod +x start_server.sh && ./start_server.sh
```

**Start Streamlit Frontend:**
```bash
./start_streamlit.sh
# or
chmod +x start_streamlit.sh && ./start_streamlit.sh
```

#### Option 2: Manual Start

**Flask Relay Server:**
```bash
python app.py
```
The server will start on `http://localhost:5000`

**Streamlit Frontend:**
```bash
streamlit run streamlit_app.py
```
The Streamlit app will open in your browser at `http://localhost:8501`

---

## 🏗️ Architecture Overview

This project follows the **Model-View-Controller (MVC)** pattern with **SOLID principles** for clean, maintainable code.

### MVC Pattern

```
┌─────────────────────────────────────────────────────────┐
│                    HTTP REQUEST                         │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                  CONTROLLER LAYER                       │
│  • Handles HTTP requests/responses                      │
│  • Validates input                                      │
│  • Delegates to services                                │
│  • Returns formatted responses                          │
│                                                          │
│  Files: app/controllers/                                │
│  - mailbox_controller.py                                │
│  - health_controller.py                                 │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                  SERVICE LAYER                          │
│  • Business logic orchestration                         │
│  • Coordinates between repositories                     │
│  • Enforces business rules                              │
│  • Transaction management                               │
│                                                          │
│  Files: app/services/                                   │
│  - mailbox_service.py                                   │
│  - validation_service.py                                │
│  - deduplication_service.py                             │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                   MODEL LAYER                           │
│  • Domain entities (Mailbox, DeviceClaim)               │
│  • Business logic in models                             │
│  • Repository pattern for data access                   │
│  • Data validation                                      │
│                                                          │
│  Files: app/models/                                     │
│  - mailbox.py                                           │
│  - device_claim.py                                      │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                   VIEW LAYER                            │
│  • Response formatting                                  │
│  • HTML generation                                      │
│  • JSON serialization                                   │
│                                                          │
│  Files: app/views/                                      │
│  - response_builder.py                                  │
└─────────────────────────────────────────────────────────┘
```

### Dependency Flow

```
app.py (Entry Point)
  │
  └─> app/__init__.py (Application Factory)
       │
       ├─> Creates Repositories (Data Layer)
       │   ├─> MailboxRepository
       │   └─> DeviceClaimRepository
       │
       ├─> Creates Services (Business Layer)
       │   ├─> MailboxService(repositories)
       │   ├─> ValidationService()
       │   └─> DeduplicationService()
       │
       ├─> Creates Controllers (Presentation Layer)
       │   ├─> MailboxController(services)
       │   └─> HealthController(service)
       │
       └─> Registers Blueprints
           ├─> create_mailbox_blueprint(controller)
           └─> create_health_blueprint(controller)
```

---

## 🎯 SOLID Principles Implementation

### 1. Single Responsibility Principle (SRP)
**Each class has ONE reason to change.**

```python
# ✅ Good: Each class has one responsibility

class MailboxController:
    """Handles HTTP requests ONLY"""
    def create_mailbox(self):
        # Extract headers, validate, delegate to service

class MailboxService:
    """Handles business logic ONLY"""
    def create_mailbox(self, ...):
        # Orchestrate mailbox creation, enforce rules

class MailboxRepository:
    """Handles data access ONLY"""
    def create(self, mailbox: Mailbox):
        # Store mailbox in database
```

**Example from code:**
- `app/controllers/mailbox_controller.py:49-115` - Controller handles HTTP only
- `app/services/mailbox_service.py:29-63` - Service handles business logic only
- `app/models/mailbox.py:99-122` - Repository handles data access only

### 2. Open/Closed Principle (OCP)
**Open for extension, closed for modification.**

```python
# ✅ Easy to add new services without modifying controllers

class MailboxController:
    def __init__(
        self,
        mailbox_service: MailboxService,
        validation_service: ValidationService,
        deduplication_service: DeduplicationService
    ):
        # New services can be injected without changing existing code
```

**Example from code:**
- `app/__init__.py:56-62` - Adding new services doesn't require changing controllers
- `app/services/` - Each service can be extended independently

### 3. Liskov Substitution Principle (LSP)
**Derived classes must be substitutable for their base classes.**

```python
# ✅ All repositories follow the same interface

class MailboxRepository:
    def create(self, mailbox: Mailbox) -> Mailbox: ...
    def find_by_id(self, mailbox_id: str) -> Optional[Mailbox]: ...
    def delete(self, mailbox_id: str) -> bool: ...

class DeviceClaimRepository:
    def create(self, claim: DeviceClaim) -> DeviceClaim: ...
    def find_by_id(self, claim_id: str) -> Optional[DeviceClaim]: ...
    def delete(self, claim_id: str) -> bool: ...

# Both can be swapped with minimal changes
```

**Example from code:**
- `app/models/mailbox.py:99` - MailboxRepository interface
- `app/models/device_claim.py:61` - DeviceClaimRepository interface
- Both follow consistent patterns and can be replaced with database implementations

### 4. Interface Segregation Principle (ISP)
**Clients shouldn't depend on interfaces they don't use.**

```python
# ✅ Services are focused and specialized

class ValidationService:
    """Only validation methods"""
    def validate_uuid(self, value: str) -> bool: ...
    def validate_create_mailbox_request(self, data: dict) -> tuple: ...

class DeduplicationService:
    """Only deduplication methods"""
    def is_duplicate_request(self, device_claim: str, request_id: str) -> bool: ...
    def mark_request_processed(self, device_claim: str, request_id: str): ...

# Controllers only depend on what they need
```

**Example from code:**
- `app/services/validation_service.py:13` - Focused on validation only
- `app/services/deduplication_service.py:10` - Focused on deduplication only
- `app/controllers/mailbox_controller.py:30-46` - Controllers use only what they need

### 5. Dependency Inversion Principle (DIP)
**Depend on abstractions, not concretions.**

```python
# ✅ Controllers depend on service abstractions, not implementations

class MailboxController:
    def __init__(
        self,
        mailbox_service: MailboxService,  # Abstraction
        validation_service: ValidationService,  # Abstraction
        deduplication_service: DeduplicationService  # Abstraction
    ):
        self._mailbox_service = mailbox_service
        self._validation_service = validation_service
        self._deduplication_service = deduplication_service

# Dependencies injected from outside (app/__init__.py)
# Easy to swap implementations for testing or different backends
```

**Example from code:**
- `app/__init__.py:44-62` - All dependencies created and injected
- `app/controllers/mailbox_controller.py:30-46` - Depends on abstractions
- Easy to mock services for testing

---

## 🔧 Project Structure

```
flask-relay-server/
├── app/                          # Main application package (MVC)
│   ├── __init__.py              # Application factory with DI
│   ├── config.py                # Configuration constants
│   │
│   ├── models/                  # Model Layer (Domain & Data)
│   │   ├── __init__.py
│   │   ├── mailbox.py          # Mailbox entity & repository
│   │   └── device_claim.py     # DeviceClaim entity & repository
│   │
│   ├── services/                # Service Layer (Business Logic)
│   │   ├── __init__.py
│   │   ├── mailbox_service.py  # Mailbox operations
│   │   ├── validation_service.py  # Input validation
│   │   └── deduplication_service.py  # Request deduplication
│   │
│   ├── controllers/             # Controller Layer (HTTP)
│   │   ├── __init__.py
│   │   ├── mailbox_controller.py  # Mailbox endpoints
│   │   └── health_controller.py   # Health/utility endpoints
│   │
│   └── views/                   # View Layer (Response Formatting)
│       ├── __init__.py
│       └── response_builder.py  # JSON/HTML responses
│
├── app.py                       # Application entry point
├── crypto_utils.py              # Encryption/decryption utilities
├── streamlit_app.py             # Streamlit frontend
├── test_workflows.py            # Integration tests
├── requirements.txt             # Python dependencies
├── start_server.sh              # Flask server launcher
├── start_streamlit.sh           # Streamlit launcher
└── README.md                    # This file
```

### Layer Responsibilities

#### **Model Layer** (`app/models/`)
- **Purpose**: Domain entities and data access
- **Contains**:
  - Domain models (Mailbox, DeviceClaim) with business logic
  - Repositories for data persistence abstraction
  - Data validation at entity level
- **Example**: `Mailbox.is_expired()` - domain logic in model

#### **Service Layer** (`app/services/`)
- **Purpose**: Business logic orchestration
- **Contains**:
  - Complex business operations
  - Coordination between repositories
  - Transaction management
  - Business rule enforcement
- **Example**: `MailboxService.create_mailbox()` - orchestrates creation

#### **Controller Layer** (`app/controllers/`)
- **Purpose**: HTTP request/response handling
- **Contains**:
  - Route definitions
  - Request parsing
  - Input validation (format)
  - Response delegation
- **Example**: `MailboxController.create_mailbox()` - handles HTTP POST /v1/m

#### **View Layer** (`app/views/`)
- **Purpose**: Response formatting
- **Contains**:
  - JSON serialization
  - HTML generation
  - Response structure
- **Example**: `ResponseBuilder.mailbox_created_response()` - formats 201 response

---

## 📖 Usage Guide

### Using the Streamlit Frontend

The frontend provides two tabs for testing different workflows:

#### 📤 Stateless Workflow

**Sender Side:**
1. Fill in credential details (title, description, image URL)
2. Add provisioning information (credential ID, issuer, valid until)
3. Click "Create Mailbox"
4. Share the generated URL and Secret with the receiver

**Receiver Side:**
1. Enter the Mailbox URL and Secret received from sender
2. Click "Retrieve Credential"
3. View the decrypted provisioning information
4. Click "Provision & Delete Mailbox" to complete the transfer

#### 🔄 Stateful Workflow

**Sender Side:**
1. Create a stateful mailbox with initial provisioning data
2. Share URL and Secret with receiver
3. Wait for receiver's response
4. Click "Check for Updates" to see receiver's data
5. Send final credentials

**Receiver Side:**
1. Retrieve initial data from mailbox
2. Generate and send response (e.g., device public key)
3. Wait for sender's final credentials
4. Click "Check for Final Credentials"
5. Provision and delete mailbox when complete

### Using the API Directly

#### Example: Create a Mailbox

```bash
curl -X POST http://localhost:5000/v1/m \
  -H "Content-Type: application/json" \
  -H "Mailbox-Request-ID: $(uuidgen)" \
  -H "Device-Claim: $(uuidgen)" \
  -d '{
    "payload": {
      "type": "AEAD_AES_128_GCM",
      "data": "base64_encoded_encrypted_data"
    },
    "displayInformation": {
      "title": "Hotel Pass",
      "description": "Room 404 Access",
      "imageURL": "https://example.com/image.jpg"
    },
    "mailboxConfiguration": {
      "accessRights": "RWD",
      "expiration": "2024-12-31T23:59:59Z"
    }
  }'
```

#### Example: Read Secure Content

```bash
curl -X POST http://localhost:5000/v1/m/{mailboxId} \
  -H "Device-Claim: your-device-claim-uuid"
```

#### Example: Delete Mailbox

```bash
curl -X DELETE http://localhost:5000/v1/m/{mailboxId} \
  -H "Device-Claim: your-device-claim-uuid"
```

---

## 📚 API Reference

### Endpoints

#### 1. CreateMailbox
- **Method**: POST
- **Path**: `/v1/m`
- **Headers**:
  - `Mailbox-Request-ID` (UUID v4, required)
  - `Device-Claim` (UUID v4, required)
  - `Device-Attestation` (optional)
- **Body**:
  ```json
  {
    "payload": {
      "type": "AEAD_AES_128_GCM" | "AEAD_AES_256_GCM",
      "data": "base64_encoded_encrypted_data"
    },
    "displayInformation": {
      "title": "string",
      "description": "string",
      "imageURL": "string"
    },
    "mailboxConfiguration": {
      "accessRights": "R" | "W" | "D" | "RW" | "RD" | "WD" | "RWD",
      "expiration": "ISO8601_datetime"
    },
    "notificationToken": "string (optional)"
  }
  ```
- **Response**: 200 OK
  ```json
  {
    "urlLink": "https://relay.example.com/v1/m/{mailboxId}",
    "isPushNotificationSupported": true
  }
  ```
- **Implementation**: `app/controllers/mailbox_controller.py:49`

#### 2. UpdateMailbox
- **Method**: PUT
- **Path**: `/v1/m/{mailboxIdentifier}`
- **Headers**:
  - `Mailbox-Request-ID` (UUID v4, required)
  - `Device-Claim` (UUID v4, required)
- **Body**:
  ```json
  {
    "payload": {
      "type": "AEAD_AES_128_GCM" | "AEAD_AES_256_GCM",
      "data": "base64_encoded_encrypted_data"
    },
    "notificationToken": "string (optional)"
  }
  ```
- **Response**: 204 No Content
- **Implementation**: `app/controllers/mailbox_controller.py:117`

#### 3. DeleteMailbox
- **Method**: DELETE
- **Path**: `/v1/m/{mailboxIdentifier}`
- **Headers**:
  - `Device-Claim` (UUID v4, required)
- **Response**: 204 No Content
- **Implementation**: `app/controllers/mailbox_controller.py:205`

#### 4. ReadDisplayInformationFromMailbox
- **Method**: GET
- **Path**: `/v1/m/{mailboxIdentifier}`
- **Response**: 200 OK (HTML)
  ```html
  <!DOCTYPE html>
  <html>
    <head><title>{title}</title></head>
    <body>
      <h1>{title}</h1>
      <p>{description}</p>
      <img src="{imageURL}" />
    </body>
  </html>
  ```
- **Implementation**: `app/controllers/mailbox_controller.py:261`

#### 5. ReadSecureContentFromMailbox
- **Method**: POST
- **Path**: `/v1/m/{mailboxIdentifier}`
- **Headers**:
  - `Device-Claim` (UUID v4, required)
- **Response**: 200 OK
  ```json
  {
    "payload": {
      "type": "AEAD_AES_128_GCM" | "AEAD_AES_256_GCM",
      "data": "base64_encoded_encrypted_data"
    }
  }
  ```
- **Implementation**: `app/controllers/mailbox_controller.py:286`

#### 6. RelinquishMailbox
- **Method**: PATCH
- **Path**: `/v1/m/{mailboxIdentifier}`
- **Headers**:
  - `Mailbox-Request-ID` (UUID v4, required)
  - `Device-Claim` (UUID v4, required)
- **Response**: 204 No Content
- **Implementation**: `app/controllers/mailbox_controller.py:336`

### HTTP Headers

#### Mailbox-Request-ID
- **Required for**: CreateMailbox, UpdateMailbox, RelinquishMailbox
- **Format**: UUID v4
- **Purpose**: Request tracking and deduplication
- **Example**: `550e8400-e29b-41d4-a716-446655440000`

#### Device-Claim
- **Required for**: All mailbox operations
- **Format**: UUID v4
- **Purpose**: Device authorization and binding
- **Example**: `6ba7b810-9dad-11d1-80b4-00c04fd430c8`

#### Device-Attestation
- **Optional for**: CreateMailbox
- **Purpose**: Remote device attestation
- **Format**: Base64-encoded attestation data

### Response Codes

| Code | Meaning | When |
|------|---------|------|
| 200 | Success | Operation completed successfully |
| 201 | Duplicate Request | Request already processed (deduplication) |
| 204 | No Content | Successful update/delete operation |
| 400 | Bad Request | Invalid data or missing required fields |
| 401 | Unauthorized | Invalid device claim for this mailbox |
| 403 | Forbidden | Access rights violation (no R/W/D permission) |
| 404 | Not Found | Mailbox doesn't exist or expired |

---

## 🔐 Security & Encryption

### Encryption Implementation

This project uses **AES-GCM** (Galois/Counter Mode) encryption, compliant with **RFC 5116**.

#### Supported Algorithms
- **AEAD_AES_128_GCM**: 128-bit key, 96-bit IV, 128-bit tag
- **AEAD_AES_256_GCM**: 256-bit key, 96-bit IV, 128-bit tag

#### Encryption Process

```python
from crypto_utils import generate_secret, encrypt_provisioning_info

# 1. Generate shared secret (sender and receiver)
secret = generate_secret(key_size=128)  # or 256

# 2. Prepare provisioning data
provisioning_info = {
    "credentialID": "hotel-room-404",
    "issuer": "Grand Hotel",
    "validUntil": "2024-12-31"
}

# 3. Encrypt
encrypted_data = encrypt_provisioning_info(provisioning_info, secret)

# Result:
# {
#   "type": "AEAD_AES_128_GCM",
#   "data": "iv_nonce||ciphertext||auth_tag (base64)"
# }
```

#### Decryption Process

```python
from crypto_utils import decrypt_provisioning_info

# Decrypt with same secret
decrypted_info = decrypt_provisioning_info(encrypted_data, secret)
# Returns: {"credentialID": "hotel-room-404", ...}
```

#### Crypto Utilities API

**File**: `crypto_utils.py`

```python
# Generate random secret key
secret = generate_secret(key_size=128)  # Returns base64 string

# Encrypt provisioning information
encrypted = encrypt_provisioning_info(
    provisioning_info: dict,
    secret: str,
    key_size: int = 128
) -> dict

# Decrypt provisioning information
decrypted = decrypt_provisioning_info(
    payload: dict,
    secret: str
) -> dict
```

### Authorization Model

#### Device Claims
- Each device generates a unique UUID (Device-Claim)
- Sender's claim is bound to mailbox at creation
- Receiver's claim is bound on first read
- Only bound devices can access mailbox content

#### Access Rights
- **R (Read)**: Can read secure content
- **W (Write)**: Can update mailbox payload
- **D (Delete)**: Can delete mailbox
- **Combinations**: RW, RD, WD, RWD

**Implementation**: `app/models/mailbox.py:43-49`

#### Request Deduplication
- Prevents replay attacks
- Uses (Device-Claim + Mailbox-Request-ID) tuple
- Returns 201 for duplicate requests
- TTL-based cleanup of processed requests

**Implementation**: `app/services/deduplication_service.py:10-36`

### Security Best Practices

#### For Developers
1. **Never log secrets or device claims**
   - Use `device_claim[:8]...` for logging
   - Never store decrypted payloads

2. **Use secure random generation**
   - `secrets.token_bytes()` for keys/IVs
   - UUID v4 for identifiers

3. **Validate all inputs**
   - Check UUID format before processing
   - Validate JSON structure
   - Sanitize display information

4. **Implement rate limiting** (recommended)
   - Prevent brute-force attacks
   - Limit requests per device claim

5. **Use HTTPS in production**
   - Never deploy with HTTP only
   - Enforce TLS 1.2 or higher

#### For Users
1. **Share URL and Secret separately**
   - Send URL via one channel (email)
   - Send Secret via another channel (SMS/QR)

2. **Use short expiration times**
   - Default: 1 hour
   - Critical credentials: 5-15 minutes

3. **Delete mailboxes after use**
   - Stateless: Receiver deletes after retrieval
   - Stateful: Last party deletes

4. **Verify display information**
   - Check title/description before accepting
   - Validate sender identity out-of-band

---

## 🧪 Testing

### Automated Tests

Run the test suite:
```bash
python test_workflows.py
```

**Test Coverage**:
- ✅ Health check endpoint
- ✅ Stateless workflow (create → read → delete)
- ✅ Stateful workflow (create → read → update → read → delete)
- ✅ Request deduplication
- ✅ Unauthorized access prevention

**File**: `test_workflows.py`

### Manual Testing with Streamlit

#### Test Stateless Workflow

1. Start both Flask and Streamlit servers
2. Go to "Stateless Workflow" tab
3. **Sender**:
   - Fill form with credential details
   - Click "Create Mailbox"
   - Note generated URL and Secret
4. **Receiver**:
   - Paste URL and Secret
   - Click "Retrieve Credential"
   - Verify decrypted data matches
   - Click "Provision & Delete Mailbox"
5. **Verify**: Mailbox is deleted (404 on subsequent access)

#### Test Stateful Workflow

1. Go to "Stateful Workflow" tab
2. **Sender**:
   - Create mailbox with initial data
   - Share URL and Secret
3. **Receiver**:
   - Retrieve initial data
   - Send response data
4. **Sender**:
   - Check for updates
   - Send final credentials
5. **Receiver**:
   - Retrieve final credentials
   - Provision and delete
6. **Verify**: Complete round-trip successful

#### Test Request Deduplication

1. Create a mailbox
2. Copy the Mailbox-Request-ID header
3. Try creating another mailbox with same Request-ID
4. **Verify**: Returns 201 with original mailbox URL

#### Test Mailbox Expiration

1. Create mailbox with 1-minute expiration:
   ```json
   "mailboxConfiguration": {
     "expiration": "2024-01-01T00:01:00Z"
   }
   ```
2. Wait for expiration
3. Attempt to read mailbox
4. **Verify**: Returns 404 (mailbox auto-deleted)

#### Test Authorization

1. Create mailbox with Device-Claim A
2. Try to read with different Device-Claim B
3. **Verify**: Returns 401 Unauthorized

### Testing Checklist

- [ ] All 6 API endpoints respond correctly
- [ ] Encryption/decryption works with 128-bit and 256-bit keys
- [ ] Stateless workflow completes end-to-end
- [ ] Stateful workflow supports multiple updates
- [ ] Duplicate requests return 201
- [ ] Expired mailboxes are auto-deleted
- [ ] Unauthorized access is prevented
- [ ] Access rights are enforced (R/W/D)
- [ ] Display information renders as HTML
- [ ] Streamlit frontend works for both workflows

---

## 🎯 Workflow Diagrams

### Stateless Workflow
```
Sender                    Relay Server              Receiver
  |                            |                         |
  |--CreateMailbox------------>|                         |
  |   (Device-Claim: A)        |                         |
  |<--URL & Secret-------------|                         |
  |                            |                         |
  |--------URL + Secret (out of band)------------------>|
  |                            |                         |
  |                            |<--ReadSecureContent-----|
  |                            |   (Device-Claim: B)     |
  |                            |----Encrypted Data------>|
  |                            | (Receiver bound)        |
  |                            |                         |
  |                            |<--DeleteMailbox---------|
  |                            |   (Device-Claim: B)     |
  |                            |----204 No Content------>|
  |                            | (Mailbox deleted)       |
```

### Stateful Workflow
```
Sender                    Relay Server              Receiver
  |                            |                         |
  |--CreateMailbox(Data1)----->|                         |
  |   (Device-Claim: A)        |                         |
  |<--URL & Secret-------------|                         |
  |                            |                         |
  |--------URL + Secret (out of band)------------------>|
  |                            |                         |
  |                            |<--ReadSecureContent-----|
  |                            |   (Device-Claim: B)     |
  |                            |----Data1--------------->|
  |                            | (Receiver bound)        |
  |                            |                         |
  |                            |<--UpdateMailbox(Data2)--|
  |                            |   (Device-Claim: B)     |
  |<--Push Notification--------|                         |
  | (if supported)             |                         |
  |                            |                         |
  |--ReadSecureContent-------->|                         |
  |   (Device-Claim: A)        |                         |
  |<--Data2--------------------|                         |
  |                            |                         |
  |--UpdateMailbox(Data3)----->|                         |
  |   (Device-Claim: A)        |                         |
  |                            |----Push Notification--->|
  |                            | (if supported)          |
  |                            |                         |
  |                            |<--ReadSecureContent-----|
  |                            |   (Device-Claim: B)     |
  |                            |----Data3--------------->|
  |                            |                         |
  |                            |<--DeleteMailbox---------|
  |                            |   (Device-Claim: B)     |
  |                            |----204 No Content------>|
```

### Data Flow Through MVC Layers

```
HTTP POST /v1/m
     │
     ▼
[MailboxController.create_mailbox()]
     │
     ├─> Extract headers (Mailbox-Request-ID, Device-Claim)
     │
     ├─> ValidationService.validate_uuid()
     │
     ├─> DeduplicationService.is_duplicate_request()
     │
     ├─> ValidationService.validate_create_mailbox_request()
     │
     ├─> MailboxService.create_mailbox()
     │        │
     │        ├─> Create Mailbox entity
     │        │
     │        ├─> MailboxRepository.create()
     │        │        │
     │        │        └─> Store in memory/database
     │        │
     │        └─> DeviceClaimRepository.create()
     │
     ├─> DeduplicationService.mark_request_processed()
     │
     └─> ResponseBuilder.mailbox_created_response()
              │
              └─> Return JSON + 200 OK
```

---

## 👨‍💻 Development Guide

### Adding a New Feature

#### Example: Add Email Notification Support

**1. Update Model (if needed)**
```python
# app/models/mailbox.py

@dataclass
class MailboxConfiguration:
    access_rights: str
    expiration: str
    email_notification: Optional[str] = None  # Add new field
```

**2. Create Service**
```python
# app/services/notification_service.py

class NotificationService:
    """Handles email/push notifications."""

    def send_email(self, email: str, subject: str, body: str):
        """Send email notification."""
        # Implementation
```

**3. Update Controller**
```python
# app/controllers/mailbox_controller.py

class MailboxController:
    def __init__(
        self,
        mailbox_service: MailboxService,
        validation_service: ValidationService,
        deduplication_service: DeduplicationService,
        notification_service: NotificationService  # Add dependency
    ):
        self._notification_service = notification_service

    def create_mailbox(self):
        # ... existing code ...

        # Add notification
        if mailbox.mailbox_configuration.email_notification:
            self._notification_service.send_email(
                mailbox.mailbox_configuration.email_notification,
                "Mailbox Created",
                f"URL: {url_link}"
            )
```

**4. Wire Dependencies**
```python
# app/__init__.py

def create_app():
    # ... existing code ...

    # Create new service
    notification_service = NotificationService()

    # Inject into controller
    mailbox_controller = MailboxController(
        mailbox_service,
        validation_service,
        deduplication_service,
        notification_service  # Add here
    )
```

### Code Style Guidelines

#### Python Style (PEP 8)
- Use 4 spaces for indentation
- Max line length: 100 characters
- Use descriptive variable names
- Add docstrings to all classes and public methods

#### Naming Conventions
- Classes: `PascalCase` (e.g., `MailboxService`)
- Functions/methods: `snake_case` (e.g., `create_mailbox`)
- Private attributes: `_leading_underscore` (e.g., `self._repository`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_EXPIRATION`)

#### Import Order
1. Standard library imports
2. Related third-party imports
3. Local application imports

```python
# Standard library
import logging
from typing import Tuple, Optional

# Third-party
from flask import request, jsonify

# Local
from app.services.mailbox_service import MailboxService
from app.models.mailbox import Mailbox
```

#### Docstring Format
```python
def create_mailbox(
    self,
    payload: Dict[str, str],
    display_information: Dict[str, str]
) -> Mailbox:
    """
    Create a new mailbox with encrypted payload.

    Args:
        payload: Encrypted credential data
        display_information: Public display metadata

    Returns:
        Created mailbox instance

    Raises:
        ValueError: If payload is invalid
    """
```

### Debugging Tips

#### Enable Debug Logging
```python
# app/config.py

class AppConfig:
    DEBUG = True  # Set to False in production
    LOG_LEVEL = logging.DEBUG
```

#### View All Mailboxes (Development Only)
```python
# Add to app/__init__.py for debugging

@app.route('/debug/mailboxes', methods=['GET'])
def debug_mailboxes():
    if not app.config['DEBUG']:
        return jsonify({"error": "Not available"}), 403

    mailboxes = mailbox_repository.get_all()
    return jsonify([vars(m) for m in mailboxes])
```

#### Test API with httpie
```bash
# Install httpie
pip install httpie

# Create mailbox
http POST localhost:5000/v1/m \
  Mailbox-Request-ID:$(uuidgen) \
  Device-Claim:$(uuidgen) \
  payload:='{"type":"AEAD_AES_128_GCM","data":"..."}' \
  displayInformation:='{"title":"Test"}'
```

---

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

### Pull Request Process

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes**
   - Follow SOLID principles
   - Maintain MVC structure
   - Add tests for new features
   - Update documentation
4. **Run tests**
   ```bash
   python test_workflows.py
   ```
5. **Commit your changes**
   ```bash
   git commit -m "Add feature: your feature description"
   ```
6. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```
7. **Open a Pull Request**

### Contribution Checklist

- [ ] Code follows PEP 8 style guidelines
- [ ] All tests pass
- [ ] New features have tests
- [ ] Documentation is updated
- [ ] SOLID principles are maintained
- [ ] MVC structure is preserved
- [ ] Security best practices are followed
- [ ] No secrets or credentials in code
- [ ] Commit messages are descriptive

### Areas for Contribution

- **Database persistence** (SQLite, PostgreSQL)
- **Push notification integration** (FCM, APNs)
- **Rate limiting** (Flask-Limiter)
- **Authentication** (API keys, OAuth)
- **Monitoring** (Prometheus metrics)
- **Docker containerization**
- **CI/CD pipeline** (GitHub Actions)
- **Additional tests** (unit, integration, e2e)
- **Documentation improvements**
- **Performance optimizations**

---

## 📝 License

This implementation is based on the public IETF draft specification: [draft-secure-credential-transfer-04](https://datatracker.ietf.org/doc/html/draft-secure-credential-transfer-04).

---

## 📧 Support

### Getting Help

1. **Check the documentation** in this README
2. **Review the code comments** for implementation details
3. **Test with Streamlit frontend** for interactive debugging
4. **Check the RFC draft** for protocol specifications

### Reporting Issues

When reporting issues, please include:
- Python version (`python --version`)
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Relevant logs or error messages

### Common Issues

#### "ModuleNotFoundError: No module named 'app'"
```bash
# Make sure you're in the project root directory
cd flask-relay-server
python app.py
```

#### "Address already in use"
```bash
# Kill process on port 5000
lsof -ti:5000 | xargs kill -9
```

#### "Invalid JSON"
```bash
# Ensure Content-Type header is set
curl -H "Content-Type: application/json" ...
```

---

## 🔄 Version History

### v2.0.0 - MVC Refactoring (Current)
- ✅ Complete MVC architecture implementation
- ✅ SOLID principles throughout codebase
- ✅ Dependency injection with application factory
- ✅ Repository pattern for data access
- ✅ Comprehensive documentation
- ✅ Updated test suite

### v1.0.0 - Initial Implementation
- ✅ Complete API endpoints (6 total)
- ✅ AES-GCM encryption (128-bit and 256-bit)
- ✅ Stateless and stateful workflows
- ✅ Streamlit frontend
- ✅ Request deduplication
- ✅ Automatic mailbox expiration

---

## 🎓 Educational Use

This implementation is ideal for:

### Learning Objectives
- **Secure Credential Transfer Protocol** - Understanding RFC draft-secure-credential-transfer-04
- **AES-GCM Encryption** - Practical cryptography implementation
- **MVC Architecture** - Clean separation of concerns
- **SOLID Principles** - Professional software design
- **Dependency Injection** - Loose coupling patterns
- **Repository Pattern** - Data access abstraction
- **REST API Design** - Best practices for HTTP APIs
- **Security Patterns** - Authorization, deduplication, expiration

### Classroom Use
- **Software Engineering Courses** - MVC and SOLID demonstrations
- **Cryptography Courses** - AES-GCM implementation
- **Web Development Courses** - Flask REST API patterns
- **Security Courses** - Secure credential transfer mechanisms

### Self-Study
- Clone and experiment with different architectures
- Add database persistence layer
- Implement additional security features
- Practice refactoring and testing

---

**Built with ❤️ following RFC standards, MVC architecture, and SOLID principles**

**Specification**: [draft-secure-credential-transfer-04](https://datatracker.ietf.org/doc/html/draft-secure-credential-transfer-04)
