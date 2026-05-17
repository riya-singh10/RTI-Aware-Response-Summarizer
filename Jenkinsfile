pipeline {
    agent any
    
    stages {
        stage('Checkout') {
            steps {
                echo 'Cloning repository...'
                git branch: 'main',
                    url: 'https://github.com/riya-singh10/RTI-Aware-Response-Summarizer.git'
            }
        }
        
        stage('Build Docker Image') {
            steps {
                echo 'Building Docker image...'
                bat 'docker build -t rti-summariser:latest .'
            }
        }
        
        stage('Push to DockerHub') {
            steps {
                echo 'Pushing to DockerHub...'
                bat 'docker tag rti-summariser:latest singhriya10/rti-summariser:latest'
                bat 'docker push singhriya10/rti-summariser:latest'
            }
        }
        
        stage('Deploy to Kubernetes') {
            steps {
                echo 'Deploying to Kubernetes...'
                bat 'kubectl apply -f k8s/deployment.yaml -n rti-app'
            }
        }
    }
    
    post {
        success {
            echo 'Pipeline completed successfully!'
        }
        failure {
            echo 'Pipeline failed!'
        }
    }
}
