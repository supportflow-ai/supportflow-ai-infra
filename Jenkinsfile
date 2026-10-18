pipeline {
    agent any
    stages {
        stage('Checkout') { steps { checkout scm } }
        stage('Validate') { steps { sh 'docker compose --env-file .env.local.example -f compose.yaml -f compose.local.yaml config --quiet' } }
        stage('System smoke') {
            steps {
                sh 'docker compose --env-file .env.local.example -f compose.yaml -f compose.local.yaml up --build -d --wait --wait-timeout 300'
                sh 'docker compose --env-file .env.local.example -f compose.yaml -f compose.local.yaml run --rm migrate seed-demo'
                sh 'bash deploy/smoke/smoke-test.sh'
            }
        }
    }
}
