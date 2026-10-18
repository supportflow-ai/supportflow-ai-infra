pipeline {
    agent any
    environment {
        BACKEND_PATH = './_sources/backend'
        WEB_PATH = './_sources/web'
        COMPOSE_PROJECT_NAME = "servicedesk-ci-${BUILD_NUMBER}"
    }
    stages {
        stage('Checkout') { steps { checkout scm } }
        stage('Pinned Sources') { steps { sh 'python3 scripts/checkout-sources.py' } }
        stage('Validate') { steps { sh 'docker compose --env-file .env.local.example -f compose.yaml -f compose.local.yaml config --quiet' } }
        stage('System smoke') {
            steps {
                sh 'docker compose --env-file .env.local.example -f compose.yaml -f compose.local.yaml up --build -d --wait --wait-timeout 300'
                sh 'docker compose --env-file .env.local.example -f compose.yaml -f compose.local.yaml run --rm migrate seed-demo'
                sh 'bash deploy/smoke/smoke-test.sh'
            }
        }
    }
    post {
        always {
            sh 'docker compose --env-file .env.local.example -f compose.yaml -f compose.local.yaml down -v'
        }
    }
}
