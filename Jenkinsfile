pipeline {
    agent any
    stages {
        stage("Checkout") {
            steps {
                checkout scm
            }
        }
        stage("Build") {
            steps {
                sh "docker build -t singhriya10/rti-summariser:latest ."
            }
        }
        stage("Push") {
            steps {
                withCredentials([usernamePassword(credentialsId: "dockerhub-creds", usernameVariable: "DOCKER_USER", passwordVariable: "DOCKER_PASS")]) {
                    sh "echo $DOCKER_PASS | docker login -u $DOCKER_USER --password-stdin"
                    sh "docker push singhriya10/rti-summariser:latest"
                }
            }
        }
        stage("Deploy") {
            steps {
                sh "kubectl apply -f k8s/deployment.yaml -n rti-app"
            }
        }
    }
}