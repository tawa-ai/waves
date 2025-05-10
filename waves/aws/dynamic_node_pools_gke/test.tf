module "mrmda_node_pool" {
  source = "../../modules/mrdma_node_pool/"

  account_id                        = "test-project"
  autoscaling                       = {
    total_min_node_count = "8"
    total_max_node_count = "0"
  }
  cluster_name                      = "test-cluster"
  disk_size                         = "1000"
  disk_type                         = "hyper-disk"
  ephemeral_storage_local_ssd_count = "1"
  gpu_accelerator                   = {
    count = "4"
    type  = "h100"
  }
  image_type                        = "cos"
  labels                            = {}
  machine_type                      = "a3-highgpu-8g"
  node_pool_name                    = "" 
  node_region                       = "us-central1"
  node_sa_email                     = "maxweirz@gmail.com" 
  node_zone                         = "a"
  placement_policy                  = {
    type = "COMPACT"
  }
  reservation_affinity              = {
    type = "<type>"
    reservations = ['test-id']
  }
}