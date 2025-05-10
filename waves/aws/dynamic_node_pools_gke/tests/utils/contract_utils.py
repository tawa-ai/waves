from dataclasses import asdict
from typing import Any, Dict

from templafirm.core.meta_table import ResourceTemplate
from templafirm.gke.gke_provider import GKEProvider

from dynamic_node_pools_gke.contract_structs import (
    MRDMANodeInformation,
    MRDMANodePoolContractDetails,
    MRDMANodePoolCreationPayload,
    MRDMAResourceCreationContract,
    RequestingResourceId,
)


def verify_input_contract(contract_kwargs: Dict[str, Any], resource: ResourceTemplate) -> None:
    contract_keys = set(contract_kwargs.keys())
    assert contract_keys.intersection(resource.template_inputs) == contract_keys


def form_input_contract_mrdma_node_pool(contract_kwargs: Dict[str, Any]) -> Dict[str, str]:
    # create provider instance for verifying contract_kwargs
    verifying_provider = GKEProvider()
    mrdma_node_pool_resource = verifying_provider["mrdma_node_pool"]
    verify_input_contract(contract_kwargs["node_information"], mrdma_node_pool_resource)

    node_information = MRDMANodeInformation(**contract_kwargs["node_information"])
    creation_payload = MRDMANodePoolCreationPayload(
        namespace=contract_kwargs["namespace"],
        node_information=node_information,
        reservation_duration=contract_kwargs["reservation_duration"],
        reservation_id=contract_kwargs["reservation_id"],
        reservation_time=contract_kwargs["reservation_time"],
        reservation_type=contract_kwargs["reservation_type"],
        resource_version=contract_kwargs["resource_version"],
    )
    resource_id = RequestingResourceId(type="controller", value="aws")
    mrdma_node_pool_request = MRDMAResourceCreationContract(
        source="tester",
        event_type="test",
        details=MRDMANodePoolContractDetails(
            payload=creation_payload,
            resource="mrdma_node_pool",
            resourceId=resource_id,
        ),
    )
    return asdict(mrdma_node_pool_request)
