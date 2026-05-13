terraform {
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
  }
}

provider "kubernetes" {
  config_path = "~/.kube/config"
}

resource "kubernetes_namespace" "rti" {
  metadata {
    name = "rti-app"
  }
}

resource "kubernetes_service" "rti_service" {
  metadata {
    name      = "rti-terraform-service"
    namespace = "rti-app"
  }
  spec {
    selector = {
      app = "rti-app"
    }
    type = "NodePort"
    port {
      port        = 8501
      target_port = 8501
      node_port   = 30002
    }
  }
}
