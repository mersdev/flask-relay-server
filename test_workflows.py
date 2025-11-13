"""
Test script for Secure Credential Transfer Relay Server
Tests both stateless and stateful workflows
"""

import requests
import json
import uuid
from datetime import datetime, timedelta, timezone
from crypto_utils import generate_secret, create_encrypted_payload, verify_and_decrypt_payload

# Configuration
RELAY_URL = "http://localhost:5000"


def test_health_check():
    """Test server health endpoint"""
    print("\n" + "="*60)
    print("TEST: Health Check")
    print("="*60)

    response = requests.get(f"{RELAY_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 200
    print("✅ Health check passed!")
    return True


def test_stateless_workflow():
    """Test complete stateless workflow"""
    print("\n" + "="*60)
    print("TEST: Stateless Workflow")
    print("="*60)

    # Generate UUIDs and secret
    sender_claim = str(uuid.uuid4())
    receiver_claim = str(uuid.uuid4())
    request_id = str(uuid.uuid4())
    secret = generate_secret(128)

    print(f"\n📤 SENDER: Creating mailbox")
    print(f"  Sender Claim: {sender_claim}")
    print(f"  Secret: {secret}")

    # Step 1: Sender creates mailbox
    provisioning_info = {
        "credentialId": "TEST-CRED-12345",
        "issuer": "Test Issuer",
        "validUntil": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "accessLevel": "full"
    }

    encrypted_payload = create_encrypted_payload(
        format_type="digitalwallet.generic.authorizationToken",
        content=provisioning_info,
        secret=secret
    )

    expiration = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat().replace('+00:00', 'Z')

    create_body = {
        "payload": encrypted_payload,
        "displayInformation": {
            "title": "Test Credential",
            "description": "Test credential for stateless workflow",
            "imageURL": "https://example.com/test.jpg"
        },
        "mailboxConfiguration": {
            "accessRights": "RWD",
            "expiration": expiration
        }
    }

    create_headers = {
        "Mailbox-Request-ID": request_id,
        "Device-Claim": sender_claim,
        "Content-Type": "application/json"
    }

    response = requests.post(f"{RELAY_URL}/v1/m", json=create_body, headers=create_headers)
    print(f"  Status: {response.status_code}")

    assert response.status_code == 200
    result = response.json()
    mailbox_url = result['urlLink']
    mailbox_id = mailbox_url.split('/')[-1]

    print(f"  ✅ Mailbox created: {mailbox_id}")
    print(f"  URL: {mailbox_url}")

    # Step 2: Receiver reads secure content
    print(f"\n📥 RECEIVER: Reading secure content")
    print(f"  Receiver Claim: {receiver_claim}")

    read_headers = {
        "Device-Claim": receiver_claim,
        "Content-Type": "application/json"
    }

    response = requests.post(f"{RELAY_URL}/v1/m/{mailbox_id}", headers=read_headers)
    print(f"  Status: {response.status_code}")

    assert response.status_code == 200
    read_result = response.json()

    print(f"  ✅ Content retrieved")
    print(f"  Display Info: {read_result['displayInformation']['title']}")

    # Decrypt and verify content
    decrypted = verify_and_decrypt_payload(read_result['payload'], secret)
    print(f"  ✅ Content decrypted")
    print(f"  Decrypted: {json.dumps(decrypted, indent=4)}")

    assert decrypted['content'] == provisioning_info
    print(f"  ✅ Content verified!")

    # Step 3: Receiver deletes mailbox
    print(f"\n🗑️ RECEIVER: Deleting mailbox")

    delete_headers = {
        "Device-Claim": receiver_claim
    }

    response = requests.delete(f"{RELAY_URL}/v1/m/{mailbox_id}", headers=delete_headers)
    print(f"  Status: {response.status_code}")

    assert response.status_code == 200
    print(f"  ✅ Mailbox deleted")

    # Verify mailbox is gone
    response = requests.post(f"{RELAY_URL}/v1/m/{mailbox_id}", headers=read_headers)
    assert response.status_code == 404
    print(f"  ✅ Mailbox confirmed deleted (404)")

    print("\n✅ STATELESS WORKFLOW TEST PASSED!")
    return True


def test_stateful_workflow():
    """Test complete stateful workflow"""
    print("\n" + "="*60)
    print("TEST: Stateful Workflow")
    print("="*60)

    # Generate UUIDs and secret
    sender_claim = str(uuid.uuid4())
    receiver_claim = str(uuid.uuid4())
    secret = generate_secret(128)

    print(f"\n📤 SENDER: Creating stateful mailbox")
    print(f"  Sender Claim: {sender_claim}")
    print(f"  Receiver Claim: {receiver_claim}")
    print(f"  Secret: {secret}")

    # Step 1: Sender creates mailbox with initial data
    initial_info = {
        "credentialId": "CAR-KEY-67890",
        "issuer": "Tesla Motors",
        "vehicleVIN": "5YJ3E1EA1KF000000",
        "step": "initial",
        "message": "Please generate device key pair"
    }

    encrypted_payload = create_encrypted_payload(
        format_type="digitalwallet.carkey.ccc",
        content=initial_info,
        secret=secret
    )

    expiration = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat().replace('+00:00', 'Z')

    create_body = {
        "payload": encrypted_payload,
        "displayInformation": {
            "title": "Tesla Car Key",
            "description": "Digital key for stateful workflow test",
            "imageURL": "https://example.com/tesla.jpg"
        },
        "mailboxConfiguration": {
            "accessRights": "RWD",
            "expiration": expiration
        }
    }

    create_headers = {
        "Mailbox-Request-ID": str(uuid.uuid4()),
        "Device-Claim": sender_claim,
        "Content-Type": "application/json"
    }

    response = requests.post(f"{RELAY_URL}/v1/m", json=create_body, headers=create_headers)
    assert response.status_code == 200

    result = response.json()
    mailbox_url = result['urlLink']
    mailbox_id = mailbox_url.split('/')[-1]

    print(f"  ✅ Mailbox created: {mailbox_id}")

    # Step 2: Receiver reads initial content
    print(f"\n📥 RECEIVER: Reading initial content")

    read_headers = {
        "Device-Claim": receiver_claim
    }

    response = requests.post(f"{RELAY_URL}/v1/m/{mailbox_id}", headers=read_headers)
    assert response.status_code == 200

    read_result = response.json()
    decrypted = verify_and_decrypt_payload(read_result['payload'], secret)

    print(f"  ✅ Initial content retrieved")
    print(f"  Step: {decrypted['content']['step']}")
    print(f"  Message: {decrypted['content']['message']}")

    # Step 3: Receiver updates mailbox with response
    print(f"\n📤 RECEIVER: Sending response")

    receiver_response = {
        "credentialId": "CAR-KEY-67890",
        "step": "receiver_response",
        "devicePublicKey": "PUBLIC-KEY-ABC123",
        "deviceId": "DEVICE-UUID-XYZ",
        "message": "Device ready for final credentials"
    }

    encrypted_response = create_encrypted_payload(
        format_type="digitalwallet.carkey.ccc",
        content=receiver_response,
        secret=secret
    )

    update_body = {
        "payload": encrypted_response
    }

    update_headers = {
        "Mailbox-Request-ID": str(uuid.uuid4()),
        "Device-Claim": receiver_claim,
        "Content-Type": "application/json"
    }

    response = requests.put(f"{RELAY_URL}/v1/m/{mailbox_id}", json=update_body, headers=update_headers)
    assert response.status_code == 200

    print(f"  ✅ Response sent")

    # Step 4: Sender reads receiver's response
    print(f"\n📥 SENDER: Reading receiver's response")

    read_headers_sender = {
        "Device-Claim": sender_claim
    }

    response = requests.post(f"{RELAY_URL}/v1/m/{mailbox_id}", headers=read_headers_sender)
    assert response.status_code == 200

    read_result = response.json()
    decrypted = verify_and_decrypt_payload(read_result['payload'], secret)

    print(f"  ✅ Response retrieved")
    print(f"  Step: {decrypted['content']['step']}")
    print(f"  Device Public Key: {decrypted['content']['devicePublicKey']}")

    # Step 5: Sender sends final credentials
    print(f"\n📤 SENDER: Sending final credentials")

    final_info = {
        "credentialId": "CAR-KEY-67890",
        "step": "final",
        "authToken": "AUTH-TOKEN-FINAL-XYZ",
        "encryptionKey": "ENC-KEY-FINAL-ABC",
        "message": "Final credentials for provisioning"
    }

    encrypted_final = create_encrypted_payload(
        format_type="digitalwallet.carkey.ccc",
        content=final_info,
        secret=secret
    )

    update_body = {
        "payload": encrypted_final
    }

    update_headers = {
        "Mailbox-Request-ID": str(uuid.uuid4()),
        "Device-Claim": sender_claim,
        "Content-Type": "application/json"
    }

    response = requests.put(f"{RELAY_URL}/v1/m/{mailbox_id}", json=update_body, headers=update_headers)
    assert response.status_code == 200

    print(f"  ✅ Final credentials sent")

    # Step 6: Receiver reads final credentials
    print(f"\n📥 RECEIVER: Reading final credentials")

    response = requests.post(f"{RELAY_URL}/v1/m/{mailbox_id}", headers=read_headers)
    assert response.status_code == 200

    read_result = response.json()
    decrypted = verify_and_decrypt_payload(read_result['payload'], secret)

    print(f"  ✅ Final credentials retrieved")
    print(f"  Step: {decrypted['content']['step']}")
    print(f"  Auth Token: {decrypted['content']['authToken']}")

    assert decrypted['content']['step'] == 'final'

    # Step 7: Receiver deletes mailbox
    print(f"\n🗑️ RECEIVER: Deleting mailbox after provisioning")

    delete_headers = {
        "Device-Claim": receiver_claim
    }

    response = requests.delete(f"{RELAY_URL}/v1/m/{mailbox_id}", headers=delete_headers)
    assert response.status_code == 200

    print(f"  ✅ Mailbox deleted")

    print("\n✅ STATEFUL WORKFLOW TEST PASSED!")
    return True


def test_duplicate_request():
    """Test request deduplication"""
    print("\n" + "="*60)
    print("TEST: Request Deduplication")
    print("="*60)

    sender_claim = str(uuid.uuid4())
    request_id = str(uuid.uuid4())
    secret = generate_secret(128)

    provisioning_info = {"test": "data"}
    encrypted_payload = create_encrypted_payload(
        format_type="digitalwallet.generic.authorizationToken",
        content=provisioning_info,
        secret=secret
    )

    expiration = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat().replace('+00:00', 'Z')

    create_body = {
        "payload": encrypted_payload,
        "displayInformation": {
            "title": "Test",
            "description": "Test",
            "imageURL": "https://example.com/test.jpg"
        },
        "mailboxConfiguration": {
            "accessRights": "RWD",
            "expiration": expiration
        }
    }

    headers = {
        "Mailbox-Request-ID": request_id,
        "Device-Claim": sender_claim,
        "Content-Type": "application/json"
    }

    # First request
    print("\n📤 Sending first request...")
    response1 = requests.post(f"{RELAY_URL}/v1/m", json=create_body, headers=headers)
    print(f"  Status: {response1.status_code}")
    assert response1.status_code == 200

    mailbox_id = response1.json()['urlLink'].split('/')[-1]
    print(f"  ✅ Mailbox created: {mailbox_id}")

    # Duplicate request (same Request-ID)
    print("\n📤 Sending duplicate request (same Request-ID)...")
    response2 = requests.post(f"{RELAY_URL}/v1/m", json=create_body, headers=headers)
    print(f"  Status: {response2.status_code}")

    assert response2.status_code == 201
    print(f"  ✅ Received 201 (duplicate detected)")

    # Cleanup
    requests.delete(f"{RELAY_URL}/v1/m/{mailbox_id}", headers={"Device-Claim": sender_claim})

    print("\n✅ DEDUPLICATION TEST PASSED!")
    return True


def test_unauthorized_access():
    """Test unauthorized access prevention"""
    print("\n" + "="*60)
    print("TEST: Unauthorized Access Prevention")
    print("="*60)

    sender_claim = str(uuid.uuid4())
    wrong_claim = str(uuid.uuid4())
    secret = generate_secret(128)

    # Create mailbox
    provisioning_info = {"test": "data"}
    encrypted_payload = create_encrypted_payload(
        format_type="digitalwallet.generic.authorizationToken",
        content=provisioning_info,
        secret=secret
    )

    expiration = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat().replace('+00:00', 'Z')

    create_body = {
        "payload": encrypted_payload,
        "displayInformation": {
            "title": "Test",
            "description": "Test",
            "imageURL": "https://example.com/test.jpg"
        },
        "mailboxConfiguration": {
            "accessRights": "RWD",
            "expiration": expiration
        }
    }

    headers = {
        "Mailbox-Request-ID": str(uuid.uuid4()),
        "Device-Claim": sender_claim,
        "Content-Type": "application/json"
    }

    response = requests.post(f"{RELAY_URL}/v1/m", json=create_body, headers=headers)
    mailbox_id = response.json()['urlLink'].split('/')[-1]

    print(f"\n✅ Mailbox created: {mailbox_id}")

    # Try to delete with wrong claim
    print("\n🚫 Attempting to delete with wrong device claim...")
    wrong_headers = {"Device-Claim": wrong_claim}

    response = requests.delete(f"{RELAY_URL}/v1/m/{mailbox_id}", headers=wrong_headers)
    print(f"  Status: {response.status_code}")

    assert response.status_code == 401
    print(f"  ✅ Unauthorized access blocked (401)")

    # Cleanup with correct claim
    requests.delete(f"{RELAY_URL}/v1/m/{mailbox_id}", headers={"Device-Claim": sender_claim})

    print("\n✅ UNAUTHORIZED ACCESS TEST PASSED!")
    return True


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("🧪 RUNNING ALL TESTS")
    print("="*60)

    tests = [
        ("Health Check", test_health_check),
        ("Stateless Workflow", test_stateless_workflow),
        ("Stateful Workflow", test_stateful_workflow),
        ("Request Deduplication", test_duplicate_request),
        ("Unauthorized Access", test_unauthorized_access)
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"\n❌ TEST FAILED: {name}")
            print(f"Error: {str(e)}")
            failed += 1

    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Total: {passed + failed}")
    print("="*60)

    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! 🎉")
    else:
        print(f"\n⚠️ {failed} test(s) failed")

    return failed == 0


if __name__ == "__main__":
    try:
        success = run_all_tests()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Tests interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {str(e)}")
        exit(1)
