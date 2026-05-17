pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                echo 'Cloning repository...'
                git branch: 'main',
                    url: 'https://github.com/riya-singh10/RTI-Aware-Response-Su>
            }
        }

        stage('Build Docker Image') {
            steps {
                echo 'Building Docker image...'
                bat 'docker build -t rti-summariser:latest .'
            }
        }

        stage('Push to DockerHub') {
                 [ Read 44 lines (converted from
