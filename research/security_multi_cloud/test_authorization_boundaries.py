#!/usr/bin/env python3
"""
Test Case: Authorization Boundaries in Multi-Cloud Environments
Objective: Evaluate authorization boundary enforcement across different cloud providers
"""

import json
import logging
import re
import sys
import time
import unittest
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CloudProvider(Enum):
    """Supported cloud providers"""

    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"


@dataclass
class ResourceIdentifier:
    """Represents a cloud resource identifier"""

    provider: CloudProvider
    resource_type: str
    resource_id: str
    region: Optional[str] = None
    account_id: Optional[str] = None

    def __str__(self) -> str:
        """String representation of the resource identifier"""
        parts = []

        if self.provider == CloudProvider.AWS:
            if self.account_id:
                parts.append(f"arn:aws:{self.resource_type}")
                parts.append(self.region or "*")
                parts.append(self.account_id)
                parts.append(self.resource_id)
                return ":".join(parts)
            return f"aws:{self.resource_type}/{self.resource_id}"

        elif self.provider == CloudProvider.GCP:
            if self.account_id:  # Project ID in GCP
                return f"//cloudresourcemanager.googleapis.com/projects/{self.account_id}/resources/{self.resource_type}/{self.resource_id}"
            return f"gcp:{self.resource_type}/{self.resource_id}"

        elif self.provider == CloudProvider.AZURE:
            if self.account_id:  # Subscription ID in Azure
                return f"/subscriptions/{self.account_id}/resourceGroups/{self.region or 'default'}/providers/Microsoft.{self.resource_type}/{self.resource_id}"
            return f"azure:{self.resource_type}/{self.resource_id}"

        return f"{self.provider.value}:{self.resource_type}/{self.resource_id}"


@dataclass
class Principal:
    """Represents a security principal (user, role, service account)"""

    provider: CloudProvider
    principal_type: str  # user, role, service-account
    principal_id: str
    account_id: Optional[str] = None

    def __str__(self) -> str:
        """String representation of the principal"""
        if self.provider == CloudProvider.AWS:
            if self.principal_type == "user":
                return f"arn:aws:iam::{self.account_id or '*'}:user/{self.principal_id}"
            elif self.principal_type == "role":
                return f"arn:aws:iam::{self.account_id or '*'}:role/{self.principal_id}"
            else:
                return f"aws:{self.principal_type}/{self.principal_id}"

        elif self.provider == CloudProvider.GCP:
            if self.principal_type == "service-account":
                return f"serviceAccount:{self.principal_id}@{self.account_id or 'unknown'}.iam.gserviceaccount.com"
            elif self.principal_type == "user":
                return f"user:{self.principal_id}"
            else:
                return f"gcp:{self.principal_type}/{self.principal_id}"

        elif self.provider == CloudProvider.AZURE:
            if self.principal_type == "user":
                return f"https://graph.microsoft.com/v1.0/users/{self.principal_id}"
            elif self.principal_type == "service-principal":
                return f"https://graph.microsoft.com/v1.0/servicePrincipals/{self.principal_id}"
            else:
                return f"azure:{self.principal_type}/{self.principal_id}"

        return f"{self.provider.value}:{self.principal_type}/{self.principal_id}"


@dataclass
class Permission:
    """Represents a permission on a resource"""

    action: (
        str  # The action being performed (e.g., s3:GetObject, compute.instances.list)
    )
    resource: ResourceIdentifier
    effect: str = "Allow"  # Allow or Deny
    conditions: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuthorizationPolicy:
    """Represents an authorization policy for a cloud resource"""

    policy_id: str
    provider: CloudProvider
    version: str = "1.0"
    principals: List[Principal] = field(default_factory=list)
    permissions: List[Permission] = field(default_factory=list)


class AuthorizationService(ABC):
    """Abstract base class for authorization services"""

    @abstractmethod
    def evaluate_access(
        self, principal: Principal, resource: ResourceIdentifier, action: str
    ) -> Tuple[bool, str]:
        """
        Evaluate if a principal has access to perform an action on a resource

        Args:
            principal: The principal requesting access
            resource: The resource to access
            action: The action to perform

        Returns:
            Tuple of (is_allowed, reason)
        """
        pass

    @abstractmethod
    def get_effective_permissions(
        self, principal: Principal, resource: ResourceIdentifier = None
    ) -> List[Permission]:
        """
        Get effective permissions for a principal, optionally scoped to a resource

        Args:
            principal: The principal to check permissions for
            resource: Optional resource to scope the permissions to

        Returns:
            List of effective permissions
        """
        pass

    @abstractmethod
    def validate_policy(self, policy: AuthorizationPolicy) -> Tuple[bool, List[str]]:
        """
        Validate an authorization policy

        Args:
            policy: The policy to validate

        Returns:
            Tuple of (is_valid, list of validation errors)
        """
        pass


class SimulatedAuthorizationService(AuthorizationService):
    """Simulated authorization service for testing cross-cloud authorization boundaries"""

    def __init__(self):
        """Initialize the service with empty policies"""
        self.policies = {}  # Map of resource_id to policy
        self.cross_cloud_mappings = {}  # Map of principal cross-cloud mappings

    def add_policy(
        self, resource: ResourceIdentifier, policy: AuthorizationPolicy
    ) -> None:
        """
        Add or update a policy for a resource

        Args:
            resource: The resource to attach the policy to
            policy: The policy to attach
        """
        resource_key = str(resource)
        self.policies[resource_key] = policy
        logger.debug(f"Added policy {policy.policy_id} to resource {resource_key}")

    def add_cross_cloud_mapping(
        self, source_principal: Principal, target_principal: Principal
    ) -> None:
        """
        Add a cross-cloud principal mapping

        Args:
            source_principal: The source principal
            target_principal: The target principal
        """
        source_key = str(source_principal)
        target_key = str(target_principal)

        if source_key not in self.cross_cloud_mappings:
            self.cross_cloud_mappings[source_key] = []

        self.cross_cloud_mappings[source_key].append(target_principal)
        logger.debug(f"Added cross-cloud mapping: {source_key} -> {target_key}")

    def evaluate_access(
        self, principal: Principal, resource: ResourceIdentifier, action: str
    ) -> Tuple[bool, str]:
        """
        Evaluate if a principal has access to perform an action on a resource

        Args:
            principal: The principal requesting access
            resource: The resource to access
            action: The action to perform

        Returns:
            Tuple of (is_allowed, reason)
        """
        # First check direct access
        allowed, reason = self._check_direct_access(principal, resource, action)
        if allowed:
            return True, reason

        # Then check cross-cloud mappings
        principal_key = str(principal)
        if principal_key in self.cross_cloud_mappings:
            for mapped_principal in self.cross_cloud_mappings[principal_key]:
                allowed, mapped_reason = self._check_direct_access(
                    mapped_principal, resource, action
                )
                if allowed:
                    return (
                        True,
                        f"Access allowed via cross-cloud mapping: {mapped_reason}",
                    )

        return False, reason

    def _check_direct_access(
        self, principal: Principal, resource: ResourceIdentifier, action: str
    ) -> Tuple[bool, str]:
        """
        Check direct access (without considering mappings)

        Args:
            principal: The principal requesting access
            resource: The resource to access
            action: The action to perform

        Returns:
            Tuple of (is_allowed, reason)
        """
        resource_key = str(resource)

        # Check if resource has a policy
        if resource_key not in self.policies:
            return False, f"No policy found for resource {resource_key}"

        policy = self.policies[resource_key]

        # Check if principal is explicitly mentioned in policy
        principal_match = False
        for policy_principal in policy.principals:
            if self._principal_matches(policy_principal, principal):
                principal_match = True
                break

        if not principal_match:
            return (
                False,
                f"Principal {principal} not allowed by policy {policy.policy_id}",
            )

        # Check permissions
        for permission in policy.permissions:
            # Check if action matches
            if self._action_matches(permission.action, action):
                # Check if resource matches
                if self._resource_matches(permission.resource, resource):
                    # Check conditions (simplified)
                    if not permission.conditions:
                        if permission.effect == "Allow":
                            return (
                                True,
                                f"Action {action} allowed on {resource} by policy {policy.policy_id}",
                            )
                        else:
                            return (
                                False,
                                f"Action {action} explicitly denied on {resource} by policy {policy.policy_id}",
                            )

        return (
            False,
            f"No matching permission for action {action} on {resource} in policy {policy.policy_id}",
        )

    def _principal_matches(
        self, policy_principal: Principal, request_principal: Principal
    ) -> bool:
        """
        Check if a principal matches a policy principal

        Args:
            policy_principal: Principal from policy
            request_principal: Principal from request

        Returns:
            True if principals match
        """
        # Exact match
        if str(policy_principal) == str(request_principal):
            return True

        # Same provider and type, wildcard ID
        if (
            policy_principal.provider == request_principal.provider
            and policy_principal.principal_type == request_principal.principal_type
            and (
                policy_principal.principal_id == "*"
                or request_principal.principal_id == "*"
            )
        ):
            return True

        # AWS specific - handle ARN pattern matching
        if (
            policy_principal.provider == CloudProvider.AWS
            and request_principal.provider == CloudProvider.AWS
        ):
            if self._match_aws_arn_pattern(
                str(policy_principal), str(request_principal)
            ):
                return True

        return False

    def _match_aws_arn_pattern(self, pattern: str, arn: str) -> bool:
        """
        Match AWS ARN pattern, supporting wildcards

        Args:
            pattern: ARN pattern with possible wildcards
            arn: ARN to match

        Returns:
            True if pattern matches ARN
        """
        # Convert ARN pattern to regex
        regex_pattern = pattern.replace("*", "[^:]*")
        regex_pattern = f"^{regex_pattern}$"

        return bool(re.match(regex_pattern, arn))

    def _action_matches(self, policy_action: str, request_action: str) -> bool:
        """
        Check if an action matches a policy action

        Args:
            policy_action: Action from policy (can contain wildcards)
            request_action: Action from request

        Returns:
            True if actions match
        """
        # Exact match
        if policy_action == request_action:
            return True

        # Wildcard match (e.g., "s3:*" matches "s3:GetObject")
        if policy_action.endswith("*"):
            prefix = policy_action[:-1]
            if request_action.startswith(prefix):
                return True

        return False

    def _resource_matches(
        self, policy_resource: ResourceIdentifier, request_resource: ResourceIdentifier
    ) -> bool:
        """
        Check if a resource matches a policy resource

        Args:
            policy_resource: Resource from policy
            request_resource: Resource from request

        Returns:
            True if resources match
        """
        # Exact match
        if str(policy_resource) == str(request_resource):
            return True

        # Same provider and type
        if (
            policy_resource.provider == request_resource.provider
            and policy_resource.resource_type == request_resource.resource_type
        ):

            # Resource ID wildcard
            if (
                policy_resource.resource_id == "*"
                or request_resource.resource_id == "*"
            ):
                return True

            # AWS specific - handle ARN pattern matching
            if policy_resource.provider == CloudProvider.AWS:
                if self._match_aws_arn_pattern(
                    str(policy_resource), str(request_resource)
                ):
                    return True

        return False

    def get_effective_permissions(
        self, principal: Principal, resource: ResourceIdentifier = None
    ) -> List[Permission]:
        """
        Get effective permissions for a principal, optionally scoped to a resource

        Args:
            principal: The principal to check permissions for
            resource: Optional resource to scope the permissions to

        Returns:
            List of effective permissions
        """
        effective_permissions = []

        # Direct permissions
        direct_permissions = self._get_direct_permissions(principal, resource)
        effective_permissions.extend(direct_permissions)

        # Permissions via cross-cloud mappings
        principal_key = str(principal)
        if principal_key in self.cross_cloud_mappings:
            for mapped_principal in self.cross_cloud_mappings[principal_key]:
                mapped_permissions = self._get_direct_permissions(
                    mapped_principal, resource
                )

                # Mark these permissions as coming from a mapping
                for perm in mapped_permissions:
                    # Add a condition to indicate the permission is from a mapping
                    conditions = perm.conditions.copy()
                    conditions["via_cross_cloud_mapping"] = {
                        "source_principal": str(principal),
                        "mapped_principal": str(mapped_principal),
                    }

                    effective_permissions.append(
                        Permission(
                            action=perm.action,
                            resource=perm.resource,
                            effect=perm.effect,
                            conditions=conditions,
                        )
                    )

        return effective_permissions

    def _get_direct_permissions(
        self, principal: Principal, resource: ResourceIdentifier = None
    ) -> List[Permission]:
        """
        Get direct permissions (without considering mappings)

        Args:
            principal: The principal to check permissions for
            resource: Optional resource to scope the permissions to

        Returns:
            List of permissions
        """
        permissions = []

        for resource_key, policy in self.policies.items():
            # Skip if resource filter is provided and doesn't match
            if resource and str(resource) != resource_key:
                continue

            # Check if principal is in policy
            principal_match = False
            for policy_principal in policy.principals:
                if self._principal_matches(policy_principal, principal):
                    principal_match = True
                    break

            if principal_match:
                for permission in policy.permissions:
                    permissions.append(permission)

        return permissions

    def validate_policy(self, policy: AuthorizationPolicy) -> Tuple[bool, List[str]]:
        """
        Validate an authorization policy

        Args:
            policy: The policy to validate

        Returns:
            Tuple of (is_valid, list of validation errors)
        """
        errors = []

        # Check for required fields
        if not policy.policy_id:
            errors.append("Policy must have an ID")

        if not policy.provider or not isinstance(policy.provider, CloudProvider):
            errors.append("Policy must have a valid provider")

        # Check principals
        if not policy.principals:
            errors.append("Policy must have at least one principal")

        # Check permissions
        if not policy.permissions:
            errors.append("Policy must have at least one permission")

        for permission in policy.permissions:
            if not permission.action:
                errors.append("Permission must have an action")

            if not permission.resource:
                errors.append("Permission must have a resource")

            if permission.effect not in ["Allow", "Deny"]:
                errors.append(f"Invalid permission effect: {permission.effect}")

        # Provider-specific validations
        if policy.provider == CloudProvider.AWS:
            aws_errors = self._validate_aws_policy(policy)
            errors.extend(aws_errors)
        elif policy.provider == CloudProvider.GCP:
            gcp_errors = self._validate_gcp_policy(policy)
            errors.extend(gcp_errors)
        elif policy.provider == CloudProvider.AZURE:
            azure_errors = self._validate_azure_policy(policy)
            errors.extend(azure_errors)

        return len(errors) == 0, errors

    def _validate_aws_policy(self, policy: AuthorizationPolicy) -> List[str]:
        """
        Validate AWS-specific policy constraints

        Args:
            policy: The policy to validate

        Returns:
            List of validation errors
        """
        errors = []

        # AWS specific validations could be added here

        return errors

    def _validate_gcp_policy(self, policy: AuthorizationPolicy) -> List[str]:
        """
        Validate GCP-specific policy constraints

        Args:
            policy: The policy to validate

        Returns:
            List of validation errors
        """
        errors = []

        # GCP specific validations could be added here

        return errors

    def _validate_azure_policy(self, policy: AuthorizationPolicy) -> List[str]:
        """
        Validate Azure-specific policy constraints

        Args:
            policy: The policy to validate

        Returns:
            List of validation errors
        """
        errors = []

        # Azure specific validations could be added here

        return errors


class AuthorizationBoundaryValidator:
    """Validates authorization boundaries across cloud providers"""

    def __init__(self, auth_service: AuthorizationService):
        """
        Initialize with an authorization service

        Args:
            auth_service: The authorization service to use
        """
        self.auth_service = auth_service
        self.violations = []

    def validate_cross_cloud_access(
        self,
        source_principal: Principal,
        target_resources: List[ResourceIdentifier],
        allowed_actions: Dict[str, List[str]],
    ) -> Tuple[bool, List[Dict]]:
        """
        Validate cross-cloud access against defined boundaries

        Args:
            source_principal: The principal to check
            target_resources: List of resources to check access to
            allowed_actions: Dict mapping resource types to allowed actions

        Returns:
            Tuple of (is_compliant, list of violations)
        """
        violations = []

        for resource in target_resources:
            # Get actions for this resource type
            resource_type = resource.resource_type
            allowed_resource_actions = allowed_actions.get(resource_type, [])

            # Get effective permissions
            permissions = self.auth_service.get_effective_permissions(
                source_principal, resource
            )

            for permission in permissions:
                # Check if permission is for an action that's not allowed
                if permission.effect == "Allow" and not self._action_is_allowed(
                    permission.action, allowed_resource_actions
                ):
                    violations.append(
                        {
                            "principal": str(source_principal),
                            "resource": str(resource),
                            "action": permission.action,
                            "expected": f"No access or only actions in {allowed_resource_actions}",
                            "violation_type": "unauthorized_action",
                        }
                    )

        self.violations = violations
        return len(violations) == 0, violations

    def _action_is_allowed(self, action: str, allowed_actions: List[str]) -> bool:
        """
        Check if an action is in the list of allowed actions

        Args:
            action: The action to check
            allowed_actions: List of allowed actions (can contain wildcards)

        Returns:
            True if action is allowed
        """
        # Check exact matches
        if action in allowed_actions or "*" in allowed_actions:
            return True

        # Check wildcard patterns
        for allowed in allowed_actions:
            if allowed.endswith("*") and action.startswith(allowed[:-1]):
                return True

        return False

    def validate_least_privilege(
        self,
        principals: List[Principal],
        resources: List[ResourceIdentifier],
        required_actions: Dict[str, Dict[str, List[str]]],
    ) -> Tuple[bool, List[Dict]]:
        """
        Validate least privilege principle across cloud boundaries

        Args:
            principals: List of principals to check
            resources: List of resources to check
            required_actions: Dict mapping principal types to dicts of resource types to required actions

        Returns:
            Tuple of (is_compliant, list of violations)
        """
        violations = []

        for principal in principals:
            principal_type = principal.principal_type

            if principal_type not in required_actions:
                continue

            required_by_resource = required_actions[principal_type]

            for resource in resources:
                resource_type = resource.resource_type

                if resource_type not in required_by_resource:
                    continue

                required_resource_actions = required_by_resource[resource_type]

                # Check each required action
                for required_action in required_resource_actions:
                    allowed, _ = self.auth_service.evaluate_access(
                        principal, resource, required_action
                    )

                    if not allowed:
                        violations.append(
                            {
                                "principal": str(principal),
                                "resource": str(resource),
                                "action": required_action,
                                "expected": "Allow",
                                "violation_type": "missing_required_permission",
                            }
                        )

        self.violations.extend(violations)
        return len(violations) == 0, violations

    def validate_separation_of_duties(
        self,
        incompatible_roles: List[Tuple[Principal, Principal]],
        resources: List[ResourceIdentifier],
        critical_actions: List[str],
    ) -> Tuple[bool, List[Dict]]:
        """
        Validate separation of duties constraints

        Args:
            incompatible_roles: List of tuples of principals that shouldn't have the same permissions
            resources: Resources to check
            critical_actions: List of critical actions that should be segregated

        Returns:
            Tuple of (is_compliant, list of violations)
        """
        violations = []

        for principal1, principal2 in incompatible_roles:
            for resource in resources:
                for action in critical_actions:
                    allowed1, _ = self.auth_service.evaluate_access(
                        principal1, resource, action
                    )
                    allowed2, _ = self.auth_service.evaluate_access(
                        principal2, resource, action
                    )

                    if allowed1 and allowed2:
                        violations.append(
                            {
                                "principal1": str(principal1),
                                "principal2": str(principal2),
                                "resource": str(resource),
                                "action": action,
                                "expected": "Only one principal should have access",
                                "violation_type": "separation_of_duties",
                            }
                        )

        self.violations.extend(violations)
        return len(violations) == 0, violations

    def generate_report(self, output_file: str = None) -> Dict:
        """
        Generate a report of authorization boundary violations

        Args:
            output_file: Optional file to write report to

        Returns:
            Report dictionary
        """
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_violations": len(self.violations),
            "violations_by_type": {},
            "violations": self.violations,
        }

        # Count violations by type
        for violation in self.violations:
            violation_type = violation.get("violation_type", "unknown")
            if violation_type not in report["violations_by_type"]:
                report["violations_by_type"][violation_type] = 0

            report["violations_by_type"][violation_type] += 1

        # Write report if requested
        if output_file:
            with open(output_file, "w") as f:
                json.dump(report, f, indent=2)

        return report


class TestAuthorizationBoundaries(unittest.TestCase):
    """Test cases for authorization boundaries in multi-cloud environments"""

    def setUp(self):
        """Set up test resources and policies"""
        self.auth_service = SimulatedAuthorizationService()
        self.validator = AuthorizationBoundaryValidator(self.auth_service)

        # Create test resources
        self.aws_s3_bucket = ResourceIdentifier(
            provider=CloudProvider.AWS,
            resource_type="s3",
            resource_id="data-bucket",
            region="us-east-1",
            account_id="123456789012",
        )

        self.gcp_storage = ResourceIdentifier(
            provider=CloudProvider.GCP,
            resource_type="storage.buckets",
            resource_id="data-bucket",
            account_id="my-gcp-project",
        )

        self.aws_ec2 = ResourceIdentifier(
            provider=CloudProvider.AWS,
            resource_type="ec2",
            resource_id="instance-1",
            region="us-east-1",
            account_id="123456789012",
        )

        # Create principals
        self.aws_user = Principal(
            provider=CloudProvider.AWS,
            principal_type="user",
            principal_id="alice",
            account_id="123456789012",
        )

        self.gcp_user = Principal(
            provider=CloudProvider.GCP,
            principal_type="user",
            principal_id="alice@example.com",
            account_id="my-gcp-project",
        )

        self.aws_admin = Principal(
            provider=CloudProvider.AWS,
            principal_type="role",
            principal_id="admin",
            account_id="123456789012",
        )

        self.gcp_admin = Principal(
            provider=CloudProvider.GCP,
            principal_type="user",
            principal_id="admin@example.com",
            account_id="my-gcp-project",
        )

        # Set up cross-cloud mappings
        self.auth_service.add_cross_cloud_mapping(self.aws_user, self.gcp_user)
        self.auth_service.add_cross_cloud_mapping(self.aws_admin, self.gcp_admin)

        # Create policies
        self._create_test_policies()

    def _create_test_policies(self):
        """Create test policies for different resources"""
        # AWS S3 bucket policy
        s3_policy = AuthorizationPolicy(
            policy_id="s3-bucket-policy",
            provider=CloudProvider.AWS,
            principals=[self.aws_user, self.aws_admin],
            permissions=[
                Permission(
                    action="s3:GetObject", resource=self.aws_s3_bucket, effect="Allow"
                ),
                Permission(
                    action="s3:PutObject", resource=self.aws_s3_bucket, effect="Allow"
                ),
                Permission(
                    action="s3:DeleteObject", resource=self.aws_s3_bucket, effect="Deny"
                ),
            ],
        )
        self.auth_service.add_policy(self.aws_s3_bucket, s3_policy)

        # AWS EC2 policy - only admin can access
        ec2_policy = AuthorizationPolicy(
            policy_id="ec2-policy",
            provider=CloudProvider.AWS,
            principals=[self.aws_admin],
            permissions=[
                Permission(action="ec2:*", resource=self.aws_ec2, effect="Allow")
            ],
        )
        self.auth_service.add_policy(self.aws_ec2, ec2_policy)

        # GCP Storage policy
        gcp_storage_policy = AuthorizationPolicy(
            policy_id="gcp-storage-policy",
            provider=CloudProvider.GCP,
            principals=[self.gcp_user, self.gcp_admin],
            permissions=[
                Permission(
                    action="storage.objects.get",
                    resource=self.gcp_storage,
                    effect="Allow",
                ),
                Permission(
                    action="storage.objects.create",
                    resource=self.gcp_storage,
                    effect="Allow",
                ),
                Permission(
                    action="storage.buckets.delete",
                    resource=self.gcp_storage,
                    effect="Deny",
                ),
            ],
        )
        self.auth_service.add_policy(self.gcp_storage, gcp_storage_policy)

    def test_direct_access(self):
        """Test direct access to resources"""
        # AWS user should be able to get objects from S3
        allowed, reason = self.auth_service.evaluate_access(
            self.aws_user, self.aws_s3_bucket, "s3:GetObject"
        )
        self.assertTrue(allowed, reason)

        # AWS user should not be able to delete objects from S3
        allowed, reason = self.auth_service.evaluate_access(
            self.aws_user, self.aws_s3_bucket, "s3:DeleteObject"
        )
        self.assertFalse(allowed, reason)

        # AWS user should not have access to EC2
        allowed, reason = self.auth_service.evaluate_access(
            self.aws_user, self.aws_ec2, "ec2:DescribeInstances"
        )
        self.assertFalse(allowed, reason)

        # AWS admin should have access to EC2
        allowed, reason = self.auth_service.evaluate_access(
            self.aws_admin, self.aws_ec2, "ec2:DescribeInstances"
        )
        self.assertTrue(allowed, reason)

    def test_cross_cloud_access(self):
        """Test cross-cloud access"""
        # AWS user should be able to access GCP storage via mapping
        allowed, reason = self.auth_service.evaluate_access(
            self.aws_user, self.gcp_storage, "storage.objects.get"
        )
        self.assertTrue(allowed, reason)

        # AWS user should not be able to delete GCP storage
        allowed, reason = self.auth_service.evaluate_access(
            self.aws_user, self.gcp_storage, "storage.buckets.delete"
        )
        self.assertFalse(allowed, reason)

        # GCP user should not be able to access AWS resources directly
        # (we didn't set up a mapping in that direction)
        allowed, reason = self.auth_service.evaluate_access(
            self.gcp_user, self.aws_s3_bucket, "s3:GetObject"
        )
        self.assertFalse(allowed, reason)

    def test_validate_cross_cloud_boundaries(self):
        """Test validation of cross-cloud access boundaries"""
        # Define allowed actions for each resource type
        allowed_actions = {
            "s3": ["s3:GetObject", "s3:ListBucket"],
            "storage.buckets": ["storage.objects.get", "storage.objects.list"],
            "ec2": [],  # No actions allowed for regular users
        }

        # Resources to check
        resources = [self.aws_s3_bucket, self.gcp_storage, self.aws_ec2]

        # Validate for AWS user
        is_compliant, violations = self.validator.validate_cross_cloud_access(
            self.aws_user, resources, allowed_actions
        )

        # Should have violations because user has s3:PutObject which is not in allowed list
        self.assertFalse(
            is_compliant, "Expected non-compliance due to excessive permissions"
        )
        self.assertTrue(any(v["action"] == "s3:PutObject" for v in violations))

    def test_least_privilege(self):
        """Test least privilege validation"""
        # Define required actions for each principal type and resource
        required_actions = {
            "user": {
                "s3": ["s3:GetObject"],
                "storage.buckets": ["storage.objects.get"],
            },
            "role": {
                "ec2": [
                    "ec2:DescribeInstances",
                    "ec2:StartInstances",
                    "ec2:StopInstances",
                ]
            },
        }

        # Principals to check
        principals = [self.aws_user, self.aws_admin]

        # Resources to check
        resources = [self.aws_s3_bucket, self.gcp_storage, self.aws_ec2]

        # Validate least privilege
        is_compliant, violations = self.validator.validate_least_privilege(
            principals, resources, required_actions
        )

        # Should be compliant for these specific required actions
        self.assertTrue(
            is_compliant, f"Expected compliance, got violations: {violations}"
        )

        # Add a required action that's not granted
        required_actions["user"]["s3"].append("s3:DeleteObject")

        is_compliant, violations = self.validator.validate_least_privilege(
            principals, resources, required_actions
        )

        # Should now have a violation
        self.assertFalse(
            is_compliant, "Expected non-compliance due to missing required permission"
        )
        self.assertTrue(any(v["action"] == "s3:DeleteObject" for v in violations))

    def test_separation_of_duties(self):
        """Test separation of duties validation"""
        # Create a new user with elevated privileges
        power_user = Principal(
            provider=CloudProvider.AWS,
            principal_type="user",
            principal_id="power-user",
            account_id="123456789012",
        )

        # Create a policy that gives power user access to EC2
        power_user_policy = AuthorizationPolicy(
            policy_id="power-user-policy",
            provider=CloudProvider.AWS,
            principals=[power_user],
            permissions=[
                Permission(action="ec2:*", resource=self.aws_ec2, effect="Allow")
            ],
        )
        self.auth_service.add_policy(self.aws_ec2, power_user_policy)

        # Define incompatible roles - regular user and admin shouldn't have same critical permissions
        incompatible_roles = [
            (self.aws_user, self.aws_admin),
            (power_user, self.aws_admin),
        ]

        # Critical actions
        critical_actions = ["ec2:TerminateInstances", "s3:DeleteBucket"]

        # Resources to check
        resources = [self.aws_s3_bucket, self.aws_ec2]

        # Validate separation of duties
        is_compliant, violations = self.validator.validate_separation_of_duties(
            incompatible_roles, resources, critical_actions
        )

        # Should be compliant since user and power user don't have delete bucket permissions
        self.assertTrue(
            is_compliant, f"Expected compliance, got violations: {violations}"
        )

        # Give both admin and power user the same critical permission
        admin_policy = AuthorizationPolicy(
            policy_id="admin-ec2-terminate-policy",
            provider=CloudProvider.AWS,
            principals=[self.aws_admin],
            permissions=[
                Permission(
                    action="ec2:TerminateInstances",
                    resource=self.aws_ec2,
                    effect="Allow",
                )
            ],
        )
        self.auth_service.add_policy(self.aws_ec2, admin_policy)

        power_user_terminate_policy = AuthorizationPolicy(
            policy_id="power-user-terminate-policy",
            provider=CloudProvider.AWS,
            principals=[power_user],
            permissions=[
                Permission(
                    action="ec2:TerminateInstances",
                    resource=self.aws_ec2,
                    effect="Allow",
                )
            ],
        )
        self.auth_service.add_policy(self.aws_ec2, power_user_terminate_policy)

        # Validate again
        is_compliant, violations = self.validator.validate_separation_of_duties(
            incompatible_roles, resources, critical_actions
        )

        # Should now have a violation
        self.assertFalse(
            is_compliant,
            "Expected non-compliance due to separation of duties violation",
        )
        self.assertTrue(
            any(v["action"] == "ec2:TerminateInstances" for v in violations)
        )

    def test_report_generation(self):
        """Test report generation"""
        # First run some validations to populate violations
        allowed_actions = {
            "s3": ["s3:GetObject"],
            "storage.buckets": ["storage.objects.get"],
            "ec2": [],
        }
        resources = [self.aws_s3_bucket, self.gcp_storage, self.aws_ec2]

        self.validator.validate_cross_cloud_access(
            self.aws_user, resources, allowed_actions
        )

        # Generate report
        report = self.validator.generate_report()

        # Verify report structure
        self.assertIn("timestamp", report)
        self.assertIn("total_violations", report)
        self.assertIn("violations_by_type", report)
        self.assertIn("violations", report)

        # Verify violations were recorded
        self.assertGreater(report["total_violations"], 0)
        self.assertGreater(len(report["violations"]), 0)


def main():
    """Run authorization boundary tests and generate report"""
    # Create the auth service and validator
    auth_service = SimulatedAuthorizationService()
    validator = AuthorizationBoundaryValidator(auth_service)

    # Find project root
    project_root = Path(__file__).parent.parent.parent

    print("\nAuthorization Boundaries in Multi-Cloud Environments")
    print("==================================================\n")

    # Set up resources for different cloud providers
    resource_setup = _setup_test_resources()

    resources = resource_setup["resources"]
    principals = resource_setup["principals"]

    # Run validations
    print("Validating cross-cloud authorization boundaries...")

    # 1. Validate cross-cloud access
    allowed_actions = {
        "s3": ["s3:GetObject", "s3:ListBucket"],
        "ec2": ["ec2:DescribeInstances"],
        "storage.buckets": ["storage.objects.get", "storage.objects.list"],
        "compute.instances": ["compute.instances.list"],
    }

    is_compliant, violations = validator.validate_cross_cloud_access(
        principals["aws_user"], resources, allowed_actions
    )

    print(
        f"\nCross-cloud access compliance: {'✅ Compliant' if is_compliant else '❌ Non-compliant'}"
    )
    print(f"Violations found: {len(violations)}")

    # 2. Validate least privilege
    required_actions = {
        "user": {"s3": ["s3:GetObject"], "storage.buckets": ["storage.objects.get"]},
        "role": {
            "ec2": ["ec2:DescribeInstances"],
            "compute.instances": ["compute.instances.list"],
        },
    }

    is_compliant, violations = validator.validate_least_privilege(
        list(principals.values()), resources, required_actions
    )

    print(
        f"\nLeast privilege compliance: {'✅ Compliant' if is_compliant else '❌ Non-compliant'}"
    )
    print(f"Violations found: {len(violations)}")

    # 3. Validate separation of duties
    incompatible_roles = [
        (principals["aws_user"], principals["aws_admin"]),
        (principals["gcp_user"], principals["gcp_admin"]),
    ]

    critical_actions = [
        "s3:DeleteBucket",
        "ec2:TerminateInstances",
        "storage.buckets.delete",
        "compute.instances.delete",
    ]

    is_compliant, violations = validator.validate_separation_of_duties(
        incompatible_roles, resources, critical_actions
    )

    print(
        f"\nSeparation of duties compliance: {'✅ Compliant' if is_compliant else '❌ Non-compliant'}"
    )
    print(f"Violations found: {len(violations)}")

    # Generate report
    report_path = (
        project_root
        / "research"
        / "security_multi_cloud"
        / "authorization_boundaries_report.json"
    )
    report = validator.generate_report(str(report_path))

    print(f"\nTotal violations found: {report['total_violations']}")
    print(f"Violations by type:")
    for vtype, count in report["violations_by_type"].items():
        print(f"  - {vtype}: {count}")

    print(f"\nDetailed report saved to: {report_path}")

    # Run unittest test cases
    print("\nRunning detailed test cases...")
    unittest.main(argv=["first-arg-is-ignored"])

    return 0


def _setup_test_resources():
    """Set up test resources and policies for manual testing"""
    auth_service = SimulatedAuthorizationService()

    # Create resources
    resources = {
        "aws_s3": ResourceIdentifier(
            provider=CloudProvider.AWS,
            resource_type="s3",
            resource_id="data-bucket",
            region="us-east-1",
            account_id="123456789012",
        ),
        "aws_ec2": ResourceIdentifier(
            provider=CloudProvider.AWS,
            resource_type="ec2",
            resource_id="instance-1",
            region="us-east-1",
            account_id="123456789012",
        ),
        "gcp_storage": ResourceIdentifier(
            provider=CloudProvider.GCP,
            resource_type="storage.buckets",
            resource_id="data-bucket",
            account_id="my-gcp-project",
        ),
        "gcp_compute": ResourceIdentifier(
            provider=CloudProvider.GCP,
            resource_type="compute.instances",
            resource_id="instance-1",
            account_id="my-gcp-project",
        ),
    }

    # Create principals
    principals = {
        "aws_user": Principal(
            provider=CloudProvider.AWS,
            principal_type="user",
            principal_id="alice",
            account_id="123456789012",
        ),
        "aws_admin": Principal(
            provider=CloudProvider.AWS,
            principal_type="role",
            principal_id="admin",
            account_id="123456789012",
        ),
        "gcp_user": Principal(
            provider=CloudProvider.GCP,
            principal_type="user",
            principal_id="alice@example.com",
            account_id="my-gcp-project",
        ),
        "gcp_admin": Principal(
            provider=CloudProvider.GCP,
            principal_type="user",
            principal_id="admin@example.com",
            account_id="my-gcp-project",
        ),
    }

    # Set up cross-cloud mappings
    auth_service.add_cross_cloud_mapping(principals["aws_user"], principals["gcp_user"])
    auth_service.add_cross_cloud_mapping(principals["gcp_user"], principals["aws_user"])
    auth_service.add_cross_cloud_mapping(
        principals["aws_admin"], principals["gcp_admin"]
    )

    # Create policies
    aws_s3_policy = AuthorizationPolicy(
        policy_id="aws-s3-policy",
        provider=CloudProvider.AWS,
        principals=[principals["aws_user"], principals["aws_admin"]],
        permissions=[
            Permission(
                action="s3:GetObject", resource=resources["aws_s3"], effect="Allow"
            ),
            Permission(
                action="s3:ListBucket", resource=resources["aws_s3"], effect="Allow"
            ),
            Permission(
                action="s3:PutObject",
                resource=resources["aws_s3"],
                effect="Allow",
                conditions={"only_if": "data_classification=public"},
            ),
            Permission(
                action="s3:DeleteObject", resource=resources["aws_s3"], effect="Deny"
            ),
        ],
    )
    auth_service.add_policy(resources["aws_s3"], aws_s3_policy)

    aws_ec2_policy = AuthorizationPolicy(
        policy_id="aws-ec2-policy",
        provider=CloudProvider.AWS,
        principals=[principals["aws_admin"]],
        permissions=[
            Permission(action="ec2:*", resource=resources["aws_ec2"], effect="Allow")
        ],
    )
    auth_service.add_policy(resources["aws_ec2"], aws_ec2_policy)

    gcp_storage_policy = AuthorizationPolicy(
        policy_id="gcp-storage-policy",
        provider=CloudProvider.GCP,
        principals=[principals["gcp_user"], principals["gcp_admin"]],
        permissions=[
            Permission(
                action="storage.objects.get",
                resource=resources["gcp_storage"],
                effect="Allow",
            ),
            Permission(
                action="storage.objects.list",
                resource=resources["gcp_storage"],
                effect="Allow",
            ),
            Permission(
                action="storage.buckets.delete",
                resource=resources["gcp_storage"],
                effect="Deny",
            ),
        ],
    )
    auth_service.add_policy(resources["gcp_storage"], gcp_storage_policy)

    gcp_compute_policy = AuthorizationPolicy(
        policy_id="gcp-compute-policy",
        provider=CloudProvider.GCP,
        principals=[principals["gcp_admin"]],
        permissions=[
            Permission(
                action="compute.instances.*",
                resource=resources["gcp_compute"],
                effect="Allow",
            )
        ],
    )
    auth_service.add_policy(resources["gcp_compute"], gcp_compute_policy)

    # Give regular user read access to compute
    gcp_compute_user_policy = AuthorizationPolicy(
        policy_id="gcp-compute-user-policy",
        provider=CloudProvider.GCP,
        principals=[principals["gcp_user"]],
        permissions=[
            Permission(
                action="compute.instances.list",
                resource=resources["gcp_compute"],
                effect="Allow",
            ),
            Permission(
                action="compute.instances.get",
                resource=resources["gcp_compute"],
                effect="Allow",
            ),
        ],
    )
    auth_service.add_policy(resources["gcp_compute"], gcp_compute_user_policy)

    return {
        "auth_service": auth_service,
        "resources": list(resources.values()),
        "principals": principals,
    }


if __name__ == "__main__":
    sys.exit(main())
