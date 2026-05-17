pipeline {
    agent any
    stages {
        stage("Checkout") {
            steps {
                echo "Checking out code..."
                checkout scm
            }
        }
        stage("Build Docker Image") {
            steps {
                echo "Building Docker image..."
                sh "docker build -t singhriya10/rti-summariser:latest ."
            }
        }
        stage("Push to DockerHub") {
            steps {
                echo "Pushing to DockerHub..."
                sh "docker push singhriya10/rti-summariser:latest"
            }
        }
        stage("Deploy to Kubernetes") {
            steps {
                echo "Deploying to Kubernetes..."
                sh "kubectl apply -f k8s/deployment.yaml -n rti-app"
            }
        }
    }
    post {
    }
}