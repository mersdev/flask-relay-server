# 🔐 Secure Credential Transfer Relay Server

A Flask-based implementation of the **Secure Credential Transfer** protocol based on [draft-secure-credential-transfer-04](https://datatracker.ietf.org/doc/html/draft-secure-credential-transfer-04).

This project provides a complete relay server for securely transferring digital credentials between devices, supporting both **stateless** and **stateful** workflows.

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

### 🎨 Streamlit Frontend
- Interactive web interface for testing
- Separate interfaces for Sender and Receiver
- Real-time workflow demonstrations
- Built-in encryption/decryption utilities

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

#### Option 1: Flask Relay Server Only
```bash
python relay_server.py
```
The server will start on `http://localhost:5000`

#### Option 2: With Streamlit Frontend
In separate terminals:

**Terminal 1 - Start Flask Server:**
```bash
python relay_server.py
```

**Terminal 2 - Start Streamlit Frontend:**
```bash
streamlit run streamlit_app.py
```
The Streamlit app will open in your browser at `http://localhost:8501`

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

## 🔧 Project Structure

```
flask-relay-server/
├── relay_server.py      # Main Flask application
├── crypto_utils.py      # Encryption/decryption utilities
├── streamlit_app.py     # Streamlit frontend
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## 🔐 Security Considerations

### Encryption
- Uses AES-GCM with 128-bit or 256-bit keys
- Random 96-bit IV for each encryption
- 128-bit authentication tag for integrity
- Compliant with RFC 5116

### Authorization
- Device Claims bind devices to mailboxes
- Only authorized devices can read/write
- Request deduplication prevents replay attacks

### Privacy
- Relay server never sees decrypted content
- No tracking of sender/receiver identities
- Automatic cleanup of expired mailboxes

### Best Practices
- Send URL and Secret over different channels
- Use short-lived mailboxes (auto-expiration)
- Delete mailboxes after successful transfer
- Validate all inputs on both client and server

## 📚 API Reference

### HTTP Headers

#### Mailbox-Request-ID
- **Required for**: CreateMailbox, UpdateMailbox, RelinquishMailbox
- **Format**: UUID v4
- **Purpose**: Request tracking and deduplication

#### Device-Claim
- **Required for**: All mailbox operations
- **Format**: UUID v4
- **Purpose**: Device authorization and binding

#### Device-Attestation
- **Optional for**: CreateMailbox
- **Purpose**: Remote device attestation

### Response Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Duplicate request (already processed) |
| 400 | Bad Request (invalid data) |
| 401 | Unauthorized (invalid device claim) |
| 403 | Forbidden (access rights violation) |
| 404 | Not Found (mailbox doesn't exist) |

## 🧪 Testing

### Test Stateless Workflow

1. Start both Flask and Streamlit servers
2. Go to "Stateless Workflow" tab
3. Fill sender form and create mailbox
4. Copy URL and Secret to receiver side
5. Retrieve and provision credential
6. Verify mailbox is deleted

### Test Stateful Workflow

1. Go to "Stateful Workflow" tab
2. Create stateful mailbox from sender
3. Receiver retrieves initial data
4. Receiver sends response
5. Sender checks for updates
6. Sender sends final credentials
7. Receiver retrieves and provisions
8. Verify complete workflow

### Test Request Deduplication

1. Create a mailbox with a specific Mailbox-Request-ID
2. Attempt to create another mailbox with the same Request-ID
3. Verify you receive 201 status code
4. Verify no duplicate mailbox was created

### Test Mailbox Expiration

1. Create a mailbox with 1-minute expiration
2. Wait for expiration time
3. Attempt to read from mailbox
4. Verify 404 response (mailbox auto-deleted)

## 🎯 Workflow Diagrams

### Stateless Workflow
```
Sender                    Relay Server              Receiver
  |                            |                         |
  |--CreateMailbox------------>|                         |
  |<--URL & isPushSupported----|                         |
  |                            |                         |
  |--------URL + Secret (out of band)------------------>|
  |                            |                         |
  |                            |<--ReadSecureContent-----|
  |                            |----Encrypted Data------>|
  |                            |                         |
  |                            |<--DeleteMailbox---------|
  |                            |----Success------------->|
```

### Stateful Workflow
```
Sender                    Relay Server              Receiver
  |                            |                         |
  |--CreateMailbox(Data1)----->|                         |
  |<--URL----------------------|                         |
  |                            |                         |
  |--------URL + Secret (out of band)------------------>|
  |                            |                         |
  |                            |<--ReadSecureContent-----|
  |                            |----Data1--------------->|
  |                            |                         |
  |                            |<--UpdateMailbox(Data2)--|
  |<--Push Notification--------|                         |
  |                            |                         |
  |--ReadSecureContent-------->|                         |
  |<--Data2--------------------|                         |
  |                            |                         |
  |--UpdateMailbox(Data3)----->|                         |
  |                            |----Push Notification--->|
  |                            |                         |
  |                            |<--ReadSecureContent-----|
  |                            |----Data3--------------->|
  |                            |                         |
  |                            |<--DeleteMailbox---------|
```

## 📝 License

This implementation is based on the public IETF draft specification.

## 🤝 Contributing

Contributions are welcome! Please ensure:
- Code follows PEP 8 style guidelines
- All tests pass
- Security best practices are maintained
- Documentation is updated

## 📧 Support

For issues or questions:
- Check the RFC draft: [draft-secure-credential-transfer-04](https://datatracker.ietf.org/doc/html/draft-secure-credential-transfer-04)
- Review the code documentation
- Test with the Streamlit frontend

## 🔄 Version History

- **v1.0.0** - Initial implementation
  - Complete API endpoints
  - AES-GCM encryption
  - Stateless and stateful workflows
  - Streamlit frontend
  - Request deduplication
  - Automatic mailbox expiration

## 🎓 Educational Use

This implementation is ideal for:
- Learning secure credential transfer protocols
- Understanding AES-GCM encryption
- Testing API security patterns
- Demonstrating device-to-device communication
- Teaching cryptographic best practices

---

**Built with ❤️ following RFC standards**
