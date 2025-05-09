#!/usr/bin/env python3
"""
Test Case: Peer Authentication Strength
Objective: Evaluate the security of peer authentication mechanisms
"""

import asyncio
import base64
import logging
import secrets
import sys
import time
from pathlib import Path

# Add project root to path so we can import HORAO modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from horao.api.authenticate import generate_auth_token
from horao.auth.validate import validate_peer

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class AuthenticationTester:
    """Test harness for evaluating authentication security"""

    def __init__(self):
        self.shared_secret = "test_shared_secret"
        self.peer_id = "test_peer_1"

    async def test_basic_authentication(self):
        """Test basic authentication functionality"""
        logger.info("Testing basic authentication flow")

        # Generate a valid token
        token = generate_auth_token(self.shared_secret, self.peer_id)

        # Validate the token
        is_valid = validate_peer(token, self.shared_secret, self.peer_id)

        logger.info(f"Basic authentication test: {'PASS' if is_valid else 'FAIL'}")
        return is_valid

    async def test_replay_attack(self):
        """Test resistance to replay attacks"""
        logger.info("Testing replay attack resistance")

        # Generate a token
        token = generate_auth_token(self.shared_secret, self.peer_id)

        # Validate the token (should succeed)
        is_valid_first = validate_peer(token, self.shared_secret, self.peer_id)

        # Wait a bit and try to reuse the same token
        await asyncio.sleep(2)

        # The token should still be valid within the expiry window
        is_valid_second = validate_peer(token, self.shared_secret, self.peer_id)

        # In a real system with nonce tracking, the second attempt should fail
        # But our simple mock implementation doesn't track nonces
        replay_vulnerable = is_valid_second

        logger.info(
            f"Replay attack resistance: {'FAIL - Vulnerable' if replay_vulnerable else 'PASS - Protected'}"
        )
        return not replay_vulnerable

    async def test_token_expiry(self):
        """Test token expiration"""
        logger.info("Testing token expiration")

        # Generate a token with very short expiry (1 second)
        token = generate_auth_token(self.shared_secret, self.peer_id, expiry=1)

        # Validate immediately (should succeed)
        is_valid_before = validate_peer(token, self.shared_secret, self.peer_id)

        # Wait for token to expire
        await asyncio.sleep(2)

        # Validate after expiry (should fail)
        is_valid_after = validate_peer(token, self.shared_secret, self.peer_id)

        expiry_working = is_valid_before and not is_valid_after

        logger.info(f"Token expiration test: {'PASS' if expiry_working else 'FAIL'}")
        return expiry_working

    async def test_token_tampering(self):
        """Test resistance to token tampering"""
        logger.info("Testing token tampering resistance")

        # Generate a valid token
        token = generate_auth_token(self.shared_secret, self.peer_id)

        # Tamper with the token
        if ":" in token:
            signature, timestamp = token.split(":", 1)
            tampered_token = f"{signature[:-3]}ABC:{timestamp}"
        else:
            tampered_token = token[:-3] + "ABC"

        # Validate the tampered token (should fail)
        is_valid = validate_peer(tampered_token, self.shared_secret, self.peer_id)

        tampering_resistant = not is_valid

        logger.info(
            f"Token tampering resistance test: {'PASS' if tampering_resistant else 'FAIL'}"
        )
        return tampering_resistant

    async def test_brute_force_resistance(self):
        """Test resistance to brute force attacks"""
        logger.info("Testing brute force resistance")

        # Generate a valid token
        token = generate_auth_token(self.shared_secret, self.peer_id)
        signature, timestamp = token.split(":", 1)

        # Attempt "brute force" with 1000 random signatures
        start_time = time.time()
        attempts = 1000
        success = False

        for _ in range(attempts):
            # Generate random signature of same length
            random_sig = base64.b64encode(secrets.token_bytes(32)).decode("utf-8")
            fake_token = f"{random_sig}:{timestamp}"

            if validate_peer(fake_token, self.shared_secret, self.peer_id):
                success = True
                break

        elapsed_time = time.time() - start_time

        # Calculate theoretically how long a real brute force would take
        sig_space_size = 256**32  # SHA-256 produces 32 bytes
        attempts_per_second = attempts / elapsed_time if elapsed_time > 0 else 0
        theoretical_years = (sig_space_size / attempts_per_second) / (
            60 * 60 * 24 * 365
        )

        brute_force_resistant = not success and theoretical_years > 1000000

        logger.info(
            f"Brute force resistance test: {'PASS' if brute_force_resistant else 'FAIL'}"
        )
        logger.info(f"Theoretical brute force would take {theoretical_years:.2e} years")

        return {
            "resistant": brute_force_resistant,
            "attempts_per_second": attempts_per_second,
            "theoretical_years": theoretical_years,
        }

    async def test_timing_attack_resistance(self):
        """Test resistance to timing attacks"""
        logger.info("Testing timing attack resistance")

        # Generate a valid token
        valid_token = generate_auth_token(self.shared_secret, self.peer_id)

        # Measure time for valid token validation
        valid_times = []
        for _ in range(100):
            start = time.perf_counter()
            validate_peer(valid_token, self.shared_secret, self.peer_id)
            valid_times.append(time.perf_counter() - start)

        # Generate an invalid token with same length
        signature, timestamp = valid_token.split(":", 1)
        invalid_sig = base64.b64encode(secrets.token_bytes(32)).decode("utf-8")
        invalid_token = f"{invalid_sig}:{timestamp}"

        # Measure time for invalid token validation
        invalid_times = []
        for _ in range(100):
            start = time.perf_counter()
            validate_peer(invalid_token, self.shared_secret, self.peer_id)
            invalid_times.append(time.perf_counter() - start)

        # Calculate statistics
        import statistics

        valid_mean = statistics.mean(valid_times)
        invalid_mean = statistics.mean(invalid_times)
        time_difference_percent = abs(valid_mean - invalid_mean) / valid_mean * 100

        # If the time difference is less than 5%, consider it resistant to timing attacks
        timing_resistant = time_difference_percent < 5.0

        logger.info(
            f"Timing attack resistance test: {'PASS' if timing_resistant else 'FAIL'}"
        )
        logger.info(f"Time difference: {time_difference_percent:.2f}%")

        return {
            "resistant": timing_resistant,
            "time_difference_percent": time_difference_percent,
            "valid_mean_time": valid_mean,
            "invalid_mean_time": invalid_mean,
        }


async def main():
    """Run the authentication security test suite"""
    logger.info("Starting peer authentication security test suite")

    tester = AuthenticationTester()

    # Run all tests
    tests = [
        ("Basic Authentication", tester.test_basic_authentication()),
        ("Replay Attack Resistance", tester.test_replay_attack()),
        ("Token Expiry", tester.test_token_expiry()),
        ("Token Tampering Resistance", tester.test_token_tampering()),
        ("Brute Force Resistance", tester.test_brute_force_resistance()),
        ("Timing Attack Resistance", tester.test_timing_attack_resistance()),
    ]

    results = {}

    for name, coro in tests:
        try:
            logger.info(f"\n--- Running test: {name} ---")
            result = await coro
            results[name] = result
        except Exception as e:
            logger.error(f"Error in test {name}: {e}")
            results[name] = {"error": str(e)}

    # Print summary
    print("\nPeer Authentication Security Test Results:")
    print("==========================================")

    passed = 0
    failed = 0

    for name, result in results.items():
        if isinstance(result, dict) and "resistant" in result:
            status = "PASS" if result["resistant"] else "FAIL"
            if result["resistant"]:
                passed += 1
            else:
                failed += 1
        elif isinstance(result, bool):
            status = "PASS" if result else "FAIL"
            if result:
                passed += 1
            else:
                failed += 1
        else:
            status = "ERROR"
            failed += 1

        print(f"{name}: {status}")

    print(f"\nSummary: {passed} passed, {failed} failed\n")

    # Detailed results for more complex tests
    if "Brute Force Resistance" in results and isinstance(
        results["Brute Force Resistance"], dict
    ):
        bf = results["Brute Force Resistance"]
        print(f"Brute Force Details:")
        print(f"  Attempts per second: {bf.get('attempts_per_second', 0):.2f}")
        print(f"  Theoretical years to break: {bf.get('theoretical_years', 0):.2e}\n")

    if "Timing Attack Resistance" in results and isinstance(
        results["Timing Attack Resistance"], dict
    ):
        ta = results["Timing Attack Resistance"]
        print(f"Timing Attack Details:")
        print(f"  Time difference: {ta.get('time_difference_percent', 0):.2f}%")
        print(f"  Valid token validation time: {ta.get('valid_mean_time', 0):.9f}s")
        print(f"  Invalid token validation time: {ta.get('invalid_mean_time', 0):.9f}s")


if __name__ == "__main__":
    asyncio.run(main())
