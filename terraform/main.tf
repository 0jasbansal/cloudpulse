terraform {
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
  }
}

variable "do_token" {
  description = "DigitalOcean API token"
  type        = string
  sensitive   = true
}

provider "digitalocean" {
  token = var.do_token
}

resource "digitalocean_droplet" "cloudpulse_node" {
  image  = "ubuntu-22-04-x64"
  name   = "cloudpulse-k8s-node"
  region = "blr1" # Bangalore region - closest to India
  size   = "s-2vcpu-4gb"

  tags = ["cloudpulse", "kubernetes"]
}

output "droplet_ip" {
  value = digitalocean_droplet.cloudpulse_node.ipv4_address
}
