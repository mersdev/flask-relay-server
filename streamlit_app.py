"""
Streamlit Frontend for Secure Credential Transfer Relay Server
Tests both Stateless and Stateful workflows
"""

import streamlit as st
import requests
import json
import uuid
from datetime import datetime, timedelta, timezone
import base64
from crypto_utils import (
    generate_secret,
    create_encrypted_payload,
    verify_and_decrypt_payload,
    encrypt_provisioning_info
)

# Configure page
st.set_page_config(
    page_title="Secure Credential Transfer Demo",
    page_icon="🔐",
    layout="wide"
)

# Default relay server URL
DEFAULT_RELAY_URL = "http://localhost:5000"

# Initialize session state
if 'relay_url' not in st.session_state:
    st.session_state.relay_url = DEFAULT_RELAY_URL

if 'sender_device_claim' not in st.session_state:
    st.session_state.sender_device_claim = str(uuid.uuid4())

if 'receiver_device_claim' not in st.session_state:
    st.session_state.receiver_device_claim = str(uuid.uuid4())

if 'secret' not in st.session_state:
    st.session_state.secret = None

if 'mailbox_url' not in st.session_state:
    st.session_state.mailbox_url = None

if 'mailbox_id' not in st.session_state:
    st.session_state.mailbox_id = None


def create_mailbox(
    relay_url: str,
    device_claim: str,
    title: str,
    description: str,
    image_url: str,
    provisioning_info: dict,
    secret: str,
    expiration_minutes: int = 60
) -> dict:
    """Create a mailbox on the relay server"""
    endpoint = f"{relay_url}/v1/m"

    # Generate request ID
    request_id = str(uuid.uuid4())

    # Calculate expiration time
    expiration = (datetime.now(timezone.utc) + timedelta(minutes=expiration_minutes)).isoformat().replace('+00:00', 'Z')

    # Encrypt provisioning info
    encrypted_payload = create_encrypted_payload(
        format_type="digitalwallet.generic.authorizationToken",
        content=provisioning_info,
        secret=secret
    )

    # Prepare request body
    body = {
        "payload": encrypted_payload,
        "displayInformation": {
            "title": title,
            "description": description,
            "imageURL": image_url
        },
        "mailboxConfiguration": {
            "accessRights": "RWD",
            "expiration": expiration
        }
    }

    headers = {
        "Mailbox-Request-ID": request_id,
        "Device-Claim": device_claim,
        "Content-Type": "application/json"
    }

    response = requests.post(endpoint, json=body, headers=headers)
    return response


def read_secure_content(relay_url: str, mailbox_id: str, device_claim: str, secret: str) -> dict:
    """Read secure content from mailbox"""
    endpoint = f"{relay_url}/v1/m/{mailbox_id}"

    headers = {
        "Device-Claim": device_claim,
        "Content-Type": "application/json"
    }

    response = requests.post(endpoint, headers=headers)

    if response.status_code == 200:
        data = response.json()
        # Decrypt payload
        encrypted_payload = data['payload']
        decrypted = verify_and_decrypt_payload(encrypted_payload, secret)
        data['decrypted_content'] = decrypted
        return data
    else:
        return None


def update_mailbox(
    relay_url: str,
    mailbox_id: str,
    device_claim: str,
    provisioning_info: dict,
    secret: str
) -> dict:
    """Update mailbox with new content"""
    endpoint = f"{relay_url}/v1/m/{mailbox_id}"

    # Generate request ID
    request_id = str(uuid.uuid4())

    # Encrypt provisioning info
    encrypted_payload = create_encrypted_payload(
        format_type="digitalwallet.generic.authorizationToken",
        content=provisioning_info,
        secret=secret
    )

    # Prepare request body
    body = {
        "payload": encrypted_payload
    }

    headers = {
        "Mailbox-Request-ID": request_id,
        "Device-Claim": device_claim,
        "Content-Type": "application/json"
    }

    response = requests.put(endpoint, json=body, headers=headers)
    return response


def delete_mailbox(relay_url: str, mailbox_id: str, device_claim: str) -> dict:
    """Delete a mailbox"""
    endpoint = f"{relay_url}/v1/m/{mailbox_id}"

    headers = {
        "Device-Claim": device_claim
    }

    response = requests.delete(endpoint, headers=headers)
    return response


# Main UI
st.title("🔐 Secure Credential Transfer Demo")
st.markdown("Test both **Stateless** and **Stateful** workflows")

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")

    relay_url = st.text_input(
        "Relay Server URL",
        value=st.session_state.relay_url,
        help="URL of the Flask relay server"
    )
    st.session_state.relay_url = relay_url

    st.divider()

    st.subheader("Device Claims")
    st.caption("Unique identifiers for sender and receiver devices")

    sender_claim = st.text_input(
        "Sender Device Claim",
        value=st.session_state.sender_device_claim,
        help="UUID for sender device"
    )
    st.session_state.sender_device_claim = sender_claim

    receiver_claim = st.text_input(
        "Receiver Device Claim",
        value=st.session_state.receiver_device_claim,
        help="UUID for receiver device"
    )
    st.session_state.receiver_device_claim = receiver_claim

    if st.button("🔄 Regenerate Claims"):
        st.session_state.sender_device_claim = str(uuid.uuid4())
        st.session_state.receiver_device_claim = str(uuid.uuid4())
        st.rerun()

    st.divider()

    # Health check
    st.subheader("Server Status")
    try:
        health_response = requests.get(f"{relay_url}/health", timeout=2)
        if health_response.status_code == 200:
            health_data = health_response.json()
            st.success("✅ Server Online")
            st.metric("Active Mailboxes", health_data.get('mailboxes', 0))
        else:
            st.error("❌ Server Error")
    except:
        st.error("❌ Server Offline")

# Main content tabs
tab1, tab2 = st.tabs(["📤 Stateless Workflow", "🔄 Stateful Workflow"])

# ============================================
# STATELESS WORKFLOW TAB
# ============================================
with tab1:
    st.header("Stateless Workflow")
    st.markdown("""
    **Flow:** Sender creates mailbox → Receiver reads content → Receiver deletes mailbox

    This is a single-transfer workflow where the sender shares credentials with the receiver in one direction.
    """)

    col1, col2 = st.columns(2)

    # SENDER SIDE
    with col1:
        st.subheader("👤 Sender Device")

        with st.form("sender_form_stateless"):
            st.markdown("**1️⃣ Create Credential Share**")

            title = st.text_input("Credential Title", value="Hotel Room Key")
            description = st.text_area("Description", value="Access to Room 404")
            image_url = st.text_input(
                "Image URL",
                value="https://example.com/hotel-key.jpg"
            )

            st.markdown("**Provisioning Information (Content)**")
            cred_id = st.text_input("Credential ID", value="HOTEL-404-KEY")
            issuer = st.text_input("Issuer", value="Grand Hotel")
            valid_until = st.text_input(
                "Valid Until",
                value=(datetime.now() + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
            )

            expiration_minutes = st.number_input(
                "Mailbox Expiration (minutes)",
                min_value=5,
                max_value=1440,
                value=60
            )

            submitted = st.form_submit_button("🚀 Create Mailbox", use_container_width=True)

            if submitted:
                try:
                    # Generate secret
                    secret = generate_secret(128)
                    st.session_state.secret = secret

                    # Prepare provisioning info
                    provisioning_info = {
                        "credentialId": cred_id,
                        "issuer": issuer,
                        "validUntil": valid_until,
                        "accessLevel": "full"
                    }

                    # Create mailbox
                    response = create_mailbox(
                        relay_url=relay_url,
                        device_claim=sender_claim,
                        title=title,
                        description=description,
                        image_url=image_url,
                        provisioning_info=provisioning_info,
                        secret=secret,
                        expiration_minutes=expiration_minutes
                    )

                    if response.status_code in [200, 201]:
                        result = response.json()
                        mailbox_url = result['urlLink']
                        st.session_state.mailbox_url = mailbox_url

                        # Extract mailbox ID from URL
                        mailbox_id = mailbox_url.split('/')[-1]
                        st.session_state.mailbox_id = mailbox_id

                        st.success("✅ Mailbox created successfully!")
                    else:
                        st.error(f"❌ Error: {response.status_code} - {response.text}")

                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

        # Display share information
        if st.session_state.mailbox_url and st.session_state.secret:
            st.divider()
            st.markdown("**2️⃣ Share with Receiver**")

            share_url = f"{st.session_state.mailbox_url}#{st.session_state.secret}"

            st.info("📱 Send these to the receiver (preferably over different channels):")

            st.text_input("Mailbox URL", value=st.session_state.mailbox_url, disabled=True)
            st.text_input("Secret", value=st.session_state.secret, disabled=True)

            st.markdown("**Or send as single URL (with fragment):**")
            st.code(share_url, language=None)

            if st.button("🗑️ Delete Mailbox", type="secondary"):
                try:
                    response = delete_mailbox(relay_url, st.session_state.mailbox_id, sender_claim)
                    if response.status_code == 200:
                        st.success("✅ Mailbox deleted!")
                        st.session_state.mailbox_url = None
                        st.session_state.mailbox_id = None
                        st.session_state.secret = None
                        st.rerun()
                    else:
                        st.error(f"❌ Error: {response.status_code}")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

    # RECEIVER SIDE
    with col2:
        st.subheader("👥 Receiver Device")

        with st.form("receiver_form_stateless"):
            st.markdown("**3️⃣ Receive Credential**")

            mailbox_url_input = st.text_input(
                "Mailbox URL",
                value=st.session_state.mailbox_url or "",
                help="URL received from sender"
            )

            secret_input = st.text_input(
                "Secret",
                value=st.session_state.secret or "",
                type="password",
                help="Secret received from sender"
            )

            retrieve_submitted = st.form_submit_button("📥 Retrieve Credential", use_container_width=True)

            if retrieve_submitted:
                try:
                    # Extract mailbox ID from URL
                    mailbox_id = mailbox_url_input.split('/')[-1].split('#')[0]

                    # Read secure content
                    result = read_secure_content(relay_url, mailbox_id, receiver_claim, secret_input)

                    if result:
                        st.success("✅ Credential retrieved successfully!")

                        st.markdown("**Display Information:**")
                        st.json(result['displayInformation'])

                        st.markdown("**Decrypted Provisioning Information:**")
                        st.json(result['decrypted_content'])

                        st.info(f"📅 Expires: {result['expiration']}")

                        # Option to delete mailbox
                        if st.button("✅ Provision & Delete Mailbox"):
                            try:
                                delete_response = delete_mailbox(relay_url, mailbox_id, receiver_claim)
                                if delete_response.status_code == 200:
                                    st.success("✅ Mailbox deleted! Credential provisioned.")
                                else:
                                    st.error(f"❌ Error deleting: {delete_response.status_code}")
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")
                    else:
                        st.error("❌ Failed to retrieve credential")

                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

# ============================================
# STATEFUL WORKFLOW TAB
# ============================================
with tab2:
    st.header("Stateful Workflow")
    st.markdown("""
    **Flow:** Sender creates mailbox → Receiver reads & updates → Sender reads update → Multiple rounds → Final provisioning

    This workflow allows multiple back-and-forth exchanges between sender and receiver.
    """)

    col1, col2 = st.columns(2)

    # SENDER SIDE (Stateful)
    with col1:
        st.subheader("👤 Sender Device")

        with st.form("sender_form_stateful"):
            st.markdown("**1️⃣ Initiate Stateful Share**")

            title_sf = st.text_input("Credential Title", value="Car Key")
            description_sf = st.text_area("Description", value="Digital key to Tesla Model 3")
            image_url_sf = st.text_input(
                "Image URL",
                value="https://example.com/car-key.jpg"
            )

            st.markdown("**Initial Provisioning Information**")
            cred_id_sf = st.text_input("Credential ID", value="CAR-KEY-12345")
            issuer_sf = st.text_input("Issuer", value="Tesla Motors")
            car_vin_sf = st.text_input("Vehicle VIN", value="5YJ3E1EA1KF000000")

            expiration_minutes_sf = st.number_input(
                "Mailbox Expiration (minutes)",
                min_value=5,
                max_value=1440,
                value=120
            )

            submitted_sf = st.form_submit_button("🚀 Create Stateful Mailbox", use_container_width=True)

            if submitted_sf:
                try:
                    # Generate secret
                    secret = generate_secret(128)
                    st.session_state.secret = secret

                    # Prepare initial provisioning info
                    provisioning_info = {
                        "credentialId": cred_id_sf,
                        "issuer": issuer_sf,
                        "vehicleVIN": car_vin_sf,
                        "step": "initial",
                        "message": "Please generate your device key pair"
                    }

                    # Create mailbox
                    response = create_mailbox(
                        relay_url=relay_url,
                        device_claim=sender_claim,
                        title=title_sf,
                        description=description_sf,
                        image_url=image_url_sf,
                        provisioning_info=provisioning_info,
                        secret=secret,
                        expiration_minutes=expiration_minutes_sf
                    )

                    if response.status_code in [200, 201]:
                        result = response.json()
                        mailbox_url = result['urlLink']
                        st.session_state.mailbox_url = mailbox_url

                        # Extract mailbox ID from URL
                        mailbox_id = mailbox_url.split('/')[-1]
                        st.session_state.mailbox_id = mailbox_id

                        st.success("✅ Stateful mailbox created!")
                    else:
                        st.error(f"❌ Error: {response.status_code} - {response.text}")

                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

        # Display share information
        if st.session_state.mailbox_url and st.session_state.secret:
            st.divider()
            st.markdown("**2️⃣ Share Information**")

            share_url = f"{st.session_state.mailbox_url}?v=c#{st.session_state.secret}"

            st.info("📱 Send these to the receiver:")
            st.text_input("Mailbox URL", value=st.session_state.mailbox_url, disabled=True, key="sf_url")
            st.text_input("Secret", value=st.session_state.secret, disabled=True, key="sf_secret")

            st.markdown("**Share URL with Car Key vertical:**")
            st.code(share_url, language=None)

            st.divider()
            st.markdown("**4️⃣ Read Receiver's Response**")

            if st.button("🔄 Check for Updates"):
                try:
                    result = read_secure_content(
                        relay_url,
                        st.session_state.mailbox_id,
                        sender_claim,
                        st.session_state.secret
                    )

                    if result:
                        st.success("✅ Content retrieved!")
                        st.markdown("**Current Provisioning Information:**")
                        st.json(result['decrypted_content'])
                    else:
                        st.error("❌ Failed to retrieve content")

                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

            st.divider()
            st.markdown("**5️⃣ Send Final Credentials**")

            with st.form("sender_update_form"):
                final_token = st.text_input("Authorization Token", value="AUTH-TOKEN-XYZ789")
                final_key = st.text_input("Encryption Key", value="ENC-KEY-ABC123")

                if st.form_submit_button("📤 Send Final Credentials"):
                    try:
                        final_info = {
                            "credentialId": cred_id_sf,
                            "step": "final",
                            "authToken": final_token,
                            "encryptionKey": final_key,
                            "message": "Final credentials for provisioning"
                        }

                        response = update_mailbox(
                            relay_url,
                            st.session_state.mailbox_id,
                            sender_claim,
                            final_info,
                            st.session_state.secret
                        )

                        if response.status_code in [200, 201]:
                            st.success("✅ Final credentials sent!")
                        else:
                            st.error(f"❌ Error: {response.status_code}")

                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

    # RECEIVER SIDE (Stateful)
    with col2:
        st.subheader("👥 Receiver Device")

        with st.form("receiver_form_stateful"):
            st.markdown("**3️⃣ Receive Initial Data**")

            mailbox_url_input_sf = st.text_input(
                "Mailbox URL",
                value=st.session_state.mailbox_url or "",
                help="URL received from sender",
                key="rec_url_sf"
            )

            secret_input_sf = st.text_input(
                "Secret",
                value=st.session_state.secret or "",
                type="password",
                help="Secret received from sender",
                key="rec_secret_sf"
            )

            retrieve_submitted_sf = st.form_submit_button("📥 Retrieve Initial Data", use_container_width=True)

            if retrieve_submitted_sf:
                try:
                    # Extract mailbox ID from URL
                    mailbox_id = mailbox_url_input_sf.split('/')[-1].split('?')[0].split('#')[0]

                    # Read secure content
                    result = read_secure_content(relay_url, mailbox_id, receiver_claim, secret_input_sf)

                    if result:
                        st.success("✅ Initial data retrieved!")

                        st.markdown("**Display Information:**")
                        st.json(result['displayInformation'])

                        st.markdown("**Decrypted Provisioning Information:**")
                        st.json(result['decrypted_content'])

                        st.info(f"📅 Expires: {result['expiration']}")
                    else:
                        st.error("❌ Failed to retrieve initial data")

                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

        st.divider()
        st.markdown("**4️⃣ Generate & Send Response**")

        with st.form("receiver_update_form"):
            device_public_key = st.text_input(
                "Device Public Key",
                value="PUBLIC-KEY-ABCDEF1234567890"
            )

            device_id = st.text_input("Device ID", value="DEVICE-UUID-XYZ")

            if st.form_submit_button("📤 Send Response to Sender"):
                try:
                    mailbox_id = mailbox_url_input_sf.split('/')[-1].split('?')[0].split('#')[0]

                    response_info = {
                        "step": "receiver_response",
                        "devicePublicKey": device_public_key,
                        "deviceId": device_id,
                        "message": "Device ready for final credentials"
                    }

                    response = update_mailbox(
                        relay_url,
                        mailbox_id,
                        receiver_claim,
                        response_info,
                        secret_input_sf
                    )

                    if response.status_code in [200, 201]:
                        st.success("✅ Response sent to sender!")
                    else:
                        st.error(f"❌ Error: {response.status_code}")

                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

        st.divider()
        st.markdown("**6️⃣ Receive Final Credentials**")

        if st.button("🔄 Check for Final Credentials"):
            try:
                mailbox_id = mailbox_url_input_sf.split('/')[-1].split('?')[0].split('#')[0]

                result = read_secure_content(relay_url, mailbox_id, receiver_claim, secret_input_sf)

                if result:
                    st.success("✅ Content retrieved!")

                    st.markdown("**Current Provisioning Information:**")
                    st.json(result['decrypted_content'])

                    if result['decrypted_content'].get('step') == 'final':
                        st.success("🎉 Final credentials received!")

                        if st.button("✅ Provision & Delete Mailbox", key="final_provision"):
                            try:
                                delete_response = delete_mailbox(relay_url, mailbox_id, receiver_claim)
                                if delete_response.status_code == 200:
                                    st.success("✅ Credential provisioned and mailbox deleted!")
                                else:
                                    st.error(f"❌ Error: {delete_response.status_code}")
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")
                else:
                    st.warning("⏳ Waiting for sender's response...")

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

# Footer
st.divider()
st.caption("🔐 Secure Credential Transfer - Based on draft-secure-credential-transfer-04")
