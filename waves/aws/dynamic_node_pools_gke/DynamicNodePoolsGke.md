# Dynamic Node Pools

Dynamic node pools is a small Lambda function that exists for the creation
of node pools on gcp. Here eventbridge events with a specified payload are
defined that encompass all required pieces of a gke node pool.

These are events created by the controller service (tbd) where that service
manages the node pool reservations (ie: statefullness, creation, deletion, tracking.)
