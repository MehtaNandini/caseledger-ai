# AWS deployment mapping

A practical AWS deployment can use:

- ECS Fargate or App Runner for the FastAPI container.
- RDS PostgreSQL for relational data.
- S3 for uploaded source files when binary document ingestion is added.
- SQS + a worker service for OCR / long-running document processing.
- CloudWatch for logs and alarms.
- Secrets Manager for database credentials and external AI-provider keys.

This file documents the deployment mapping only. The local project does not claim an AWS environment has been provisioned.
