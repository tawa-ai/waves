from dataclasses import dataclass
from typing import Any


@dataclass
class RequestingResourceId:
    """Abstract requesting resource id struct."""

    type: str
    value: str


@dataclass
class ResourceContractDetails:
    """Abstract requesting resource contract details."""

    payload: Any
    resource: str
    resourceId: RequestingResourceId
    eventType: str = "ResourceCreation"


@dataclass
class MRDMANodeInformation:
    """Required information for creating mrdma node pool on gke."""

    cluster_name: str
    disk_size: int
    disk_type: str
    ephemeral_storage_local_ssd_count: int
    gpu_accelerator_count: int
    gpu_accelerator_type: str
    gcp_project_id: str
    image_type: str
    machine_type: str
    node_region: str
    node_zone: str
    placement_policy_type: str
    total_max_node_count: int
    total_min_node_count: int


@dataclass
class MRDMANodePoolCreationPayload:
    """Node pool creation payload, full required info for operation."""

    namespace: str
    node_information: MRDMANodeInformation
    reservation_duration: int
    reservation_id: str
    reservation_time: str
    reservation_type: str
    resource_version: str


@dataclass
class MRDMANodePoolContractDetails(ResourceContractDetails):
    """Concrete contract details for mrdma node creation."""

    payload: MRDMANodePoolCreationPayload


@dataclass
class ResourceCreationContract:
    """Abstract resource creation contract."""

    source: str  # event source
    event_type: str  # type of event
    details: Any


@dataclass
class MRDMAResourceCreationContract(ResourceCreationContract):
    """Concrete resource creation contract."""

    details: MRDMANodePoolContractDetails
