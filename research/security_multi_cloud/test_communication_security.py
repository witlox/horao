#!/usr/bin/env python3
"""
Test Case: Multi-Cloud Communication Security
Objective: Evaluate secure communication patterns between clouds
"""

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import random
import secrets
import sys
import time
import uuid
from enum import Enum
from pathlib import Path
from typing import Any, Dict

# Add project root to path so we can import HORAO modules
sys.path.append(str(Path(__file__).parent.parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """Security level for communication tests"""

    NONE = 0  # No security (plain text)
    BASIC = 1  # Basic authentication
    HMAC = 2  # HMAC-based message authentication
    TOKEN = 3  # Token-based authentication
    TLS = 4  # TLS with certificate validation


class Message:
    """Represents a message exchanged between cloud controllers"""

    def __init__(
        self, sender: str, recipient: str, message_type: str, payload: Dict[str, Any]
    ):
        """
        Initialize a message

        Args:
            sender: ID of the sending controller
            recipient: ID of the receiving controller
            message_type: Type of message
            payload: Message content
        """
        self.id = str(uuid.uuid4())
        self.sender = sender
        self.recipient = recipient
        self.message_type = message_type
        self.payload = payload
        self.timestamp = time.time()
        self.signature = None
        self.hmac = None

    def to_dict(self) -> Dict:
        """Convert message to dictionary"""
        return {
            "id": self.id,
            "sender": self.sender,
            "recipient": self.recipient,
            "type": self.message_type,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "signature": self.signature,
            "hmac": self.hmac,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Message":
        """Create message from dictionary"""
        msg = cls(
            sender=data["sender"],
            recipient=data["recipient"],
            message_type=data["type"],
            payload=data["payload"],
        )
        msg.id = data["id"]
        msg.timestamp = data["timestamp"]
        msg.signature = data.get("signature")
        msg.hmac = data.get("hmac")
        return msg

    def sign(self, secret_key: str) -> None:
        """
        Sign the message with a secret key

        Args:
            secret_key: The key used for signing
        """
        # Create a canonical representation of the message
        canonical = f"{self.id}:{self.sender}:{self.recipient}:{self.timestamp}"

        if isinstance(self.payload, dict):
            # Sort payload keys for deterministic signing
            for k in sorted(self.payload.keys()):
                canonical += f":{k}={self.payload[k]}"

        # Create HMAC signature
        h = hmac.new(
            secret_key.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256
        )
        self.hmac = base64.b64encode(h.digest()).decode("utf-8")

    def verify(self, secret_key: str) -> bool:
        """
        Verify the message signature

        Args:
            secret_key: The key used for signing

        Returns:
            True if signature is valid, False otherwise
        """
        if not self.hmac:
            return False

        # Recreate canonical representation
        canonical = f"{self.id}:{self.sender}:{self.recipient}:{self.timestamp}"

        if isinstance(self.payload, dict):
            # Sort payload keys for deterministic verification
            for k in sorted(self.payload.keys()):
                canonical += f":{k}={self.payload[k]}"

        # Create HMAC signature
        h = hmac.new(
            secret_key.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256
        )
        expected_hmac = base64.b64encode(h.digest()).decode("utf-8")

        # Verify signature using constant-time comparison
        return hmac.compare_digest(self.hmac, expected_hmac)


class CloudController:
    """Mock cloud controller for security testing"""

    def __init__(self, controller_id: str, cloud_type: str):
        """
        Initialize a cloud controller

        Args:
            controller_id: Unique identifier for the controller
            cloud_type: Type of cloud provider (aws, gcp, azure)
        """
        self.controller_id = controller_id
        self.cloud_type = cloud_type
        self.secret_keys = {}  # Map of peer_id -> shared_secret
        self.received_messages = []
        self.security_level = SecurityLevel.BASIC
        self.channel_broken = False  # Simulate communication failures

        # Security metrics
        self.auth_failures = 0
        self.valid_messages = 0
        self.invalid_messages = 0

    def add_peer(self, peer_id: str, shared_secret: str = None):
        """
        Add a peer controller with a shared secret

        Args:
            peer_id: ID of the peer controller
            shared_secret: Secret key shared with this peer (if None, generates a new one)
        """
        if shared_secret is None:
            shared_secret = secrets.token_hex(32)
        self.secret_keys[peer_id] = shared_secret
        return shared_secret

    def send_message(
        self, recipient_id: str, message_type: str, payload: Dict[str, Any]
    ) -> Message:
        """
        Send a message to another controller

        Args:
            recipient_id: ID of the recipient controller
            message_type: Type of message
            payload: Message content

        Returns:
            The created message
        """
        if self.channel_broken:
            logger.warning(
                f"Channel from {self.controller_id} to {recipient_id} is broken"
            )
            return None

        message = Message(
            sender=self.controller_id,
            recipient=recipient_id,
            message_type=message_type,
            payload=payload,
        )

        # Apply security measures based on security level
        if self.security_level == SecurityLevel.HMAC:
            if recipient_id in self.secret_keys:
                message.sign(self.secret_keys[recipient_id])
            else:
                logger.error(f"No shared secret for peer {recipient_id}")
                return None

        return message

    def receive_message(self, message: Message) -> bool:
        """
        Process a received message

        Args:
            message: The received message

        Returns:
            True if message is valid, False otherwise
        """
        if message.recipient != self.controller_id:
            logger.warning(f"Message not intended for this controller: {message.id}")
            self.invalid_messages += 1
            return False

        # Apply security checks based on security level
        valid = True

        if self.security_level == SecurityLevel.BASIC:
            # Basic verification just checks sender and recipient
            valid = (
                message.sender in self.secret_keys
                and message.recipient == self.controller_id
            )

        elif self.security_level == SecurityLevel.HMAC:
            # Verify HMAC signature
            if message.sender in self.secret_keys:
                valid = message.verify(self.secret_keys[message.sender])
                if not valid:
                    logger.warning(
                        f"HMAC verification failed for message: {message.id}"
                    )
                    self.auth_failures += 1
            else:
                logger.warning(f"Unknown sender: {message.sender}")
                valid = False
                self.auth_failures += 1

        if valid:
            self.received_messages.append(message)
            self.valid_messages += 1
        else:
            self.invalid_messages += 1

        return valid

    def get_security_metrics(self) -> Dict:
        """Get security-related metrics"""
        return {
            "controller_id": self.controller_id,
            "cloud_type": self.cloud_type,
            "security_level": self.security_level.name,
            "auth_failures": self.auth_failures,
            "valid_messages": self.valid_messages,
            "invalid_messages": self.invalid_messages,
            "total_messages": self.valid_messages + self.invalid_messages,
            "message_types_received": self._count_message_types(),
        }

    def _count_message_types(self) -> Dict[str, int]:
        """Count received messages by type"""
        counts = {}
        for msg in self.received_messages:
            counts[msg.message_type] = counts.get(msg.message_type, 0) + 1
        return counts


class NetworkSimulator:
    """Simulates network conditions for testing communication security"""

    def __init__(self):
        """Initialize the network simulator"""
        self.controllers = {}  # Map of controller_id -> CloudController
        self.packet_loss_rate = 0.0  # Probability of packet loss
        self.man_in_the_middle = False  # Whether MITM attacks are active
        self.message_log = []  # Log of all messages

    def add_controller(self, controller: CloudController):
        """Add a controller to the network"""
        self.controllers[controller.controller_id] = controller

    def establish_trust(self, controller1_id: str, controller2_id: str) -> bool:
        """
        Establish trust between two controllers by setting up shared secrets

        Args:
            controller1_id: ID of the first controller
            controller2_id: ID of the second controller

        Returns:
            True if trust was established, False otherwise
        """
        if (
            controller1_id not in self.controllers
            or controller2_id not in self.controllers
        ):
            return False

        controller1 = self.controllers[controller1_id]
        controller2 = self.controllers[controller2_id]

        # Generate a shared secret
        shared_secret = secrets.token_hex(32)

        # Share it with both controllers
        controller1.add_peer(controller2_id, shared_secret)
        controller2.add_peer(controller1_id, shared_secret)

        return True

    async def deliver_message(self, message: Message, delay: float = 0.0) -> bool:
        """
        Deliver a message from one controller to another

        Args:
            message: The message to deliver
            delay: Simulated network delay in seconds

        Returns:
            True if delivery was successful, False otherwise
        """
        if not message:
            return False

        self.message_log.append(message.to_dict())

        # Check for packet loss
        if self.packet_loss_rate > 0 and random.random() < self.packet_loss_rate:
            logger.info(f"Message lost: {message.id}")
            return False

        # Wait for the delay to simulate network latency
        if delay > 0:
            await asyncio.sleep(delay)

        # Check if recipient exists
        if message.recipient not in self.controllers:
            logger.warning(f"Recipient not found: {message.recipient}")
            return False

        recipient = self.controllers[message.recipient]

        # Simulate man-in-the-middle attack if enabled
        if self.man_in_the_middle and message.security_level == SecurityLevel.BASIC:
            logger.info(f"MITM attack on message: {message.id}")
            # Modify the payload to simulate an attack
            if isinstance(message.payload, dict):
                message.payload["compromised"] = True

        # Deliver the message
        success = recipient.receive_message(message)
        return success

    def set_security_level(self, security_level: SecurityLevel):
        """Set the security level for all controllers"""
        for controller in self.controllers.values():
            controller.security_level = security_level

    def get_message_stats(self) -> Dict:
        """Get statistics about messages in the network"""
        total_messages = len(self.message_log)
        message_types = {}
        senders = {}

        for msg in self.message_log:
            message_types[msg["type"]] = message_types.get(msg["type"], 0) + 1
            senders[msg["sender"]] = senders.get(msg["sender"], 0) + 1

        return {
            "total_messages": total_messages,
            "message_types": message_types,
            "messages_by_sender": senders,
        }


async def test_basic_message_delivery():
    """Test basic message delivery between controllers"""
    # Setup controllers
    aws = CloudController("aws-1", "aws")
    gcp = CloudController("gcp-1", "gcp")
    azure = CloudController("azure-1", "azure")

    # Setup network
    network = NetworkSimulator()
    network.add_controller(aws)
    network.add_controller(gcp)
    network.add_controller(azure)

    # Establish trust relationships
    network.establish_trust("aws-1", "gcp-1")
    network.establish_trust("aws-1", "azure-1")
    network.establish_trust("gcp-1", "azure-1")

    # Send messages
    message1 = aws.send_message(
        "gcp-1", "resource.query", {"resource_type": "vm", "region": "us-west1"}
    )
    await network.deliver_message(message1, delay=0.1)

    message2 = gcp.send_message(
        "aws-1",
        "resource.response",
        {"resource_count": 5, "resources": ["vm-1", "vm-2"]},
    )
    await network.deliver_message(message2, delay=0.1)

    # Verify messages were received
    assert len(gcp.received_messages) == 1, "GCP should have received 1 message"
    assert len(aws.received_messages) == 1, "AWS should have received 1 message"
    assert (
        len(azure.received_messages) == 0
    ), "Azure should not have received any message"

    return {
        "test": "basic_message_delivery",
        "success": True,
        "aws_messages": len(aws.received_messages),
        "gcp_messages": len(gcp.received_messages),
        "azure_messages": len(azure.received_messages),
    }


async def test_security_levels():
    """Test different security levels for messages"""
    results = []

    for level in [SecurityLevel.NONE, SecurityLevel.BASIC, SecurityLevel.HMAC]:
        # Setup controllers
        aws = CloudController("aws-1", "aws")
        gcp = CloudController("gcp-1", "gcp")

        # Set security level
        aws.security_level = level
        gcp.security_level = level

        # Setup network
        network = NetworkSimulator()
        network.add_controller(aws)
        network.add_controller(gcp)

        # Establish trust
        network.establish_trust("aws-1", "gcp-1")

        # Send legitimate message
        message = aws.send_message(
            "gcp-1", "resource.query", {"resource_type": "storage"}
        )

        success = await network.deliver_message(message)

        # Try to forge a message (no proper signing)
        forged = Message(
            sender="aws-1",  # Pretend to be AWS
            recipient="gcp-1",
            message_type="resource.command",
            payload={"action": "delete_all"},
        )

        # For HMAC level, this should fail
        # For BASIC or NONE, it might succeed
        forge_success = await network.deliver_message(forged)

        results.append(
            {
                "security_level": level.name,
                "legitimate_message_success": success,
                "forged_message_success": forge_success,
                "forgery_detected": not forge_success,
                "gcp_valid_messages": gcp.valid_messages,
                "gcp_invalid_messages": gcp.invalid_messages,
                "gcp_auth_failures": gcp.auth_failures,
            }
        )

    return {"test": "security_levels", "results": results}


async def test_mitm_attacks():
    """Test resilience to man-in-the-middle attacks"""
    results = {}

    for level in [SecurityLevel.BASIC, SecurityLevel.HMAC]:
        # Setup controllers
        aws = CloudController("aws-1", "aws")
        gcp = CloudController("gcp-1", "gcp")

        # Set security level
        aws.security_level = level
        gcp.security_level = level

        # Setup network with MITM enabled
        network = NetworkSimulator()
        network.man_in_the_middle = True
        network.add_controller(aws)
        network.add_controller(gcp)

        # Establish trust
        network.establish_trust("aws-1", "gcp-1")

        # Exchange 10 messages
        message_successes = 0
        message_failures = 0

        for i in range(10):
            message = aws.send_message(
                "gcp-1",
                "resource.update",
                {"resource_id": f"res-{i}", "status": "active"},
            )

            success = await network.deliver_message(message)
            if success:
                message_successes += 1
            else:
                message_failures += 1

        # Check if any messages were tampered with
        tampered_count = sum(
            1
            for msg in gcp.received_messages
            if isinstance(msg.payload, dict) and msg.payload.get("compromised")
        )

        results[level.name] = {
            "message_successes": message_successes,
            "message_failures": message_failures,
            "tampered_messages": tampered_count,
            "mitm_prevented": tampered_count == 0,
        }

    return {"test": "mitm_attacks", "results": results}


async def test_communication_patterns():
    """Test different communication patterns between controllers"""
    # Setup controllers
    aws = CloudController("aws-1", "aws")
    gcp = CloudController("gcp-1", "gcp")
    azure = CloudController("azure-1", "azure")

    # Setup with HMAC security
    aws.security_level = SecurityLevel.HMAC
    gcp.security_level = SecurityLevel.HMAC
    azure.security_level = SecurityLevel.HMAC

    # Setup network
    network = NetworkSimulator()
    network.add_controller(aws)
    network.add_controller(gcp)
    network.add_controller(azure)

    # Establish trust between all pairs
    network.establish_trust("aws-1", "gcp-1")
    network.establish_trust("aws-1", "azure-1")
    network.establish_trust("gcp-1", "azure-1")

    # Test 1: Point-to-point message
    p2p_msg = aws.send_message("gcp-1", "resource.query", {"region": "us-west1"})
    p2p_success = await network.deliver_message(p2p_msg)

    # Test 2: Broadcast - one message to all controllers
    broadcast_successes = 0
    broadcast_failures = 0

    for recipient_id in ["gcp-1", "azure-1"]:
        broadcast_msg = aws.send_message(
            recipient_id, "system.notification", {"message": "Maintenance scheduled"}
        )
        if await network.deliver_message(broadcast_msg):
            broadcast_successes += 1
        else:
            broadcast_failures += 1

    # Test 3: Chain communication (AWS → GCP → Azure)
    chain_complete = False

    # First hop: AWS to GCP
    hop1_msg = aws.send_message(
        "gcp-1",
        "resource.forward",
        {"final_recipient": "azure-1", "payload": {"action": "check_status"}},
    )

    hop1_success = await network.deliver_message(hop1_msg)

    # Second hop: GCP to Azure (only if first hop succeeded)
    hop2_success = False
    if hop1_success:
        # Extract the forwarded payload
        forwarded_msg = gcp.received_messages[-1]
        forward_data = forwarded_msg.payload

        if forward_data.get("final_recipient") == "azure-1":
            # Forward to final recipient
            hop2_msg = gcp.send_message(
                "azure-1", "resource.status", forward_data.get("payload", {})
            )
            hop2_success = await network.deliver_message(hop2_msg)

    chain_complete = hop1_success and hop2_success

    return {
        "test": "communication_patterns",
        "results": {
            "point_to_point_success": p2p_success,
            "broadcast_success_rate": broadcast_successes
            / (broadcast_successes + broadcast_failures),
            "chain_communication_complete": chain_complete,
            "aws_messages_sent": 3,  # 1 p2p + 2 broadcast
            "gcp_messages_sent": 1 if hop1_success else 0,  # Forward to Azure
            "aws_messages_received": 0,
            "gcp_messages_received": 1 + (1 if p2p_success else 0),  # From AWS
            "azure_messages_received": 1 + (1 if hop2_success else 0),  # From AWS + GCP
        },
    }


async def run_all_tests():
    """Run all communication security tests"""
    results = {}

    # Run individual tests
    results["basic_message_delivery"] = await test_basic_message_delivery()
    results["security_levels"] = await test_security_levels()
    results["mitm_attacks"] = await test_mitm_attacks()
    results["communication_patterns"] = await test_communication_patterns()

    # Calculate overall security metrics
    security_score = 0
    max_score = 0

    # Score basic message delivery
    if results["basic_message_delivery"]["success"]:
        security_score += 10
    max_score += 10

    # Score security levels
    for level_result in results["security_levels"]["results"]:
        if level_result["security_level"] == "HMAC":
            # HMAC should detect forgery
            if level_result["forgery_detected"]:
                security_score += 30
            max_score += 30
        elif level_result["security_level"] == "BASIC":
            # Basic might detect forgery
            if level_result["forgery_detected"]:
                security_score += 10
            max_score += 10

    # Score MITM resilience
    if results["mitm_attacks"]["results"]["HMAC"]["mitm_prevented"]:
        security_score += 30
    max_score += 30

    # Score communication patterns
    comm_results = results["communication_patterns"]["results"]
    if comm_results["point_to_point_success"]:
        security_score += 5
    max_score += 5

    if comm_results["broadcast_success_rate"] > 0.9:
        security_score += 5
    max_score += 5

    if comm_results["chain_communication_complete"]:
        security_score += 10
    max_score += 10

    # Calculate final score as percentage
    final_score = (security_score / max_score) * 100 if max_score > 0 else 0

    # Add summary to results
    results["summary"] = {
        "security_score": security_score,
        "max_score": max_score,
        "percentage_score": final_score,
        "secure_communication_rating": (
            "Excellent"
            if final_score >= 90
            else (
                "Good"
                if final_score >= 75
                else (
                    "Satisfactory"
                    if final_score >= 60
                    else "Needs Improvement" if final_score >= 40 else "Inadequate"
                )
            )
        ),
    }

    return results


async def main():
    """Run all communication security tests and print results"""
    logger.info("Starting multi-cloud communication security tests")

    results = await run_all_tests()

    # Save results to file
    with open("communication_security_results.json", "w") as f:
        json.dump(results, f, indent=2)

    # Print summary to console
    print("\nMulti-Cloud Communication Security Test Results")
    print("===============================================")
    print(
        f"Overall Security Rating: {results['summary']['secure_communication_rating']}"
    )
    print(
        f"Security Score: {results['summary']['security_score']} / {results['summary']['max_score']}"
    )
    print(f"Percentage Score: {results['summary']['percentage_score']:.1f}%\n")

    print("Key Findings:")

    # Report on MITM protection
    hmac_mitm = results["mitm_attacks"]["results"]["HMAC"]["mitm_prevented"]
    basic_mitm = results["mitm_attacks"]["results"]["BASIC"]["mitm_prevented"]
    print(
        f"- HMAC protection against MITM attacks: {'Effective' if hmac_mitm else 'Ineffective'}"
    )
    print(
        f"- Basic protection against MITM attacks: {'Effective' if basic_mitm else 'Ineffective'}"
    )

    # Report on forgery protection
    hmac_forgery = False
    basic_forgery = False
    for level_result in results["security_levels"]["results"]:
        if level_result["security_level"] == "HMAC":
            hmac_forgery = level_result["forgery_detected"]
        elif level_result["security_level"] == "BASIC":
            basic_forgery = level_result["forgery_detected"]

    print(
        f"- HMAC protection against message forgery: {'Effective' if hmac_forgery else 'Ineffective'}"
    )
    print(
        f"- Basic protection against message forgery: {'Effective' if basic_forgery else 'Ineffective'}"
    )

    # Report on communication patterns
    chain_complete = results["communication_patterns"]["results"][
        "chain_communication_complete"
    ]
    print(
        f"- Multi-hop message forwarding: {'Successful' if chain_complete else 'Failed'}"
    )

    print("\nDetailed results saved to communication_security_results.json")


if __name__ == "__main__":
    asyncio.run(main())
